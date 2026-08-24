import hmac
import os
from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from agente_ventas import add_assistant_message
from db import (
    get_conversacion,
    get_cuenta_by_id,
    get_historial,
    get_mensajes,
    guardar_historial,
    listar_conversaciones,
    listar_cuentas,
    marcar_visto,
    registrar_mensaje,
    set_estado,
    set_modo,
    set_nombre,
    set_notas,
)
from graph_api import send_message

panel_bp = Blueprint("panel", __name__, url_prefix="/panel")

ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("autenticado"):
            if request.path.startswith("/panel/api/"):
                return jsonify(error="no autenticado"), 401
            return redirect(url_for("panel.login"))
        return f(*args, **kwargs)

    return wrapper


@panel_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "")
        password = request.form.get("password", "")
        if hmac.compare_digest(usuario, ADMIN_USERNAME) and hmac.compare_digest(
            password, ADMIN_PASSWORD
        ):
            session["autenticado"] = True
            return redirect(url_for("panel.inbox"))
        return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html", error=None)


@panel_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("panel.login"))


@panel_bp.route("/")
@login_required
def inbox():
    return render_template("inbox.html")


@panel_bp.route("/api/cuentas")
@login_required
def api_cuentas():
    return jsonify(listar_cuentas())


@panel_bp.route("/api/conversaciones")
@login_required
def api_conversaciones():
    cuenta_id = request.args.get("cuenta_id", type=int)
    if not cuenta_id:
        return jsonify(error="cuenta_id requerido"), 400
    return jsonify(listar_conversaciones(cuenta_id))


@panel_bp.route("/api/conversaciones/<int:conversacion_id>")
@login_required
def api_conversacion_detalle(conversacion_id):
    conversacion = get_conversacion(conversacion_id)
    if not conversacion:
        return jsonify(error="no encontrada"), 404
    return jsonify(conversacion)


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/mensajes")
@login_required
def api_mensajes(conversacion_id):
    after_id = request.args.get("after_id", type=int)
    return jsonify(get_mensajes(conversacion_id, after_id))


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/visto", methods=["POST"])
@login_required
def api_marcar_visto(conversacion_id):
    marcar_visto(conversacion_id)
    return jsonify(status="ok")


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/estado", methods=["POST"])
@login_required
def api_set_estado(conversacion_id):
    estado = (request.get_json(silent=True) or {}).get("estado")
    if estado not in ("abierta", "pendiente", "resuelta"):
        return jsonify(error="estado inválido"), 400
    set_estado(conversacion_id, estado)
    return jsonify(status="ok")


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/modo", methods=["POST"])
@login_required
def api_set_modo(conversacion_id):
    modo = (request.get_json(silent=True) or {}).get("modo")
    if modo not in ("bot", "humano"):
        return jsonify(error="modo inválido"), 400
    set_modo(conversacion_id, modo)
    return jsonify(status="ok")


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/nombre", methods=["POST"])
@login_required
def api_set_nombre(conversacion_id):
    nombre = (request.get_json(silent=True) or {}).get("nombre", "").strip()
    set_nombre(conversacion_id, nombre or None)
    return jsonify(status="ok")


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/notas", methods=["POST"])
@login_required
def api_set_notas(conversacion_id):
    notas = (request.get_json(silent=True) or {}).get("notas", "")
    set_notas(conversacion_id, notas)
    return jsonify(status="ok")


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/responder", methods=["POST"])
@login_required
def api_responder(conversacion_id):
    texto = (request.get_json(silent=True) or {}).get("texto", "").strip()
    if not texto:
        return jsonify(error="texto vacío"), 400

    conversacion = get_conversacion(conversacion_id)
    if not conversacion:
        return jsonify(error="conversación no encontrada"), 404

    cuenta = get_cuenta_by_id(conversacion["cuenta_id"])
    send_message(cuenta, conversacion["telefono"], texto)
    registrar_mensaje(conversacion_id, "saliente", texto)

    # Se agrega también al historial JSONB para que el bot tenga en cuenta
    # la respuesta manual si retoma la conversación más adelante.
    messages = get_historial(conversacion["cuenta_id"], conversacion["telefono"])
    add_assistant_message(messages, texto)
    guardar_historial(conversacion["cuenta_id"], conversacion["telefono"], messages)

    return jsonify(status="ok")
