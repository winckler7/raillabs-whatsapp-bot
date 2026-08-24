import hmac
import os
from functools import wraps

from flask import Blueprint, Response, jsonify, redirect, render_template, request, session, url_for

from agente_ventas import add_assistant_message
from db import (
    borrar_etiqueta,
    borrar_plantilla,
    crear_etiqueta,
    crear_plantilla,
    get_conversacion,
    get_cuenta_by_id,
    get_estados_salientes,
    get_historial,
    get_media,
    get_mensajes,
    guardar_historial,
    listar_conversaciones,
    listar_cuentas,
    listar_etiquetas,
    listar_plantillas,
    marcar_visto,
    registrar_mensaje,
    registrar_mensaje_con_media,
    set_archivada,
    set_estado,
    set_etiquetas_conversacion,
    set_modo,
    set_nombre,
    set_notas,
)
from graph_api import enviar_media, send_message, subir_media

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
    archivadas = request.args.get("archivadas") == "1"
    return jsonify(listar_conversaciones(cuenta_id, archivadas=archivadas))


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


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/estados")
@login_required
def api_estados_entrega(conversacion_id):
    return jsonify(get_estados_salientes(conversacion_id))


@panel_bp.route("/api/mensajes/<int:mensaje_id>/media")
@login_required
def api_media(mensaje_id):
    media = get_media(mensaje_id)
    if not media:
        return jsonify(error="no encontrado"), 404
    return Response(media["contenido"], mimetype=media["mime_type"])


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


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/archivar", methods=["POST"])
@login_required
def api_archivar(conversacion_id):
    archivada = bool((request.get_json(silent=True) or {}).get("archivada"))
    set_archivada(conversacion_id, archivada)
    return jsonify(status="ok")


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/etiquetas", methods=["POST"])
@login_required
def api_set_etiquetas(conversacion_id):
    etiqueta_ids = (request.get_json(silent=True) or {}).get("etiqueta_ids", [])
    set_etiquetas_conversacion(conversacion_id, etiqueta_ids)
    return jsonify(status="ok")


@panel_bp.route("/api/etiquetas")
@login_required
def api_listar_etiquetas():
    cuenta_id = request.args.get("cuenta_id", type=int)
    if not cuenta_id:
        return jsonify(error="cuenta_id requerido"), 400
    return jsonify(listar_etiquetas(cuenta_id))


@panel_bp.route("/api/etiquetas", methods=["POST"])
@login_required
def api_crear_etiqueta():
    body = request.get_json(silent=True) or {}
    cuenta_id = body.get("cuenta_id")
    nombre = (body.get("nombre") or "").strip()
    color = body.get("color") or "#667781"
    if not cuenta_id or not nombre:
        return jsonify(error="cuenta_id y nombre requeridos"), 400
    etiqueta_id = crear_etiqueta(cuenta_id, nombre, color)
    return jsonify(id=etiqueta_id, nombre=nombre, color=color)


@panel_bp.route("/api/etiquetas/<int:etiqueta_id>", methods=["DELETE"])
@login_required
def api_borrar_etiqueta(etiqueta_id):
    borrar_etiqueta(etiqueta_id)
    return jsonify(status="ok")


@panel_bp.route("/api/plantillas")
@login_required
def api_listar_plantillas():
    cuenta_id = request.args.get("cuenta_id", type=int)
    if not cuenta_id:
        return jsonify(error="cuenta_id requerido"), 400
    return jsonify(listar_plantillas(cuenta_id))


@panel_bp.route("/api/plantillas", methods=["POST"])
@login_required
def api_crear_plantilla():
    body = request.get_json(silent=True) or {}
    cuenta_id = body.get("cuenta_id")
    texto = (body.get("texto") or "").strip()
    if not cuenta_id or not texto:
        return jsonify(error="cuenta_id y texto requeridos"), 400
    plantilla_id = crear_plantilla(cuenta_id, texto)
    return jsonify(id=plantilla_id, texto=texto)


@panel_bp.route("/api/plantillas/<int:plantilla_id>", methods=["DELETE"])
@login_required
def api_borrar_plantilla(plantilla_id):
    borrar_plantilla(plantilla_id)
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
    wa_id = send_message(cuenta, conversacion["telefono"], texto)
    registrar_mensaje(conversacion_id, "saliente", texto, wa_message_id=wa_id)

    # Se agrega también al historial JSONB para que el bot tenga en cuenta
    # la respuesta manual si retoma la conversación más adelante.
    messages = get_historial(conversacion["cuenta_id"], conversacion["telefono"])
    add_assistant_message(messages, texto)
    guardar_historial(conversacion["cuenta_id"], conversacion["telefono"], messages)

    return jsonify(status="ok")


@panel_bp.route("/api/conversaciones/<int:conversacion_id>/responder-media", methods=["POST"])
@login_required
def api_responder_media(conversacion_id):
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify(error="archivo requerido"), 400

    conversacion = get_conversacion(conversacion_id)
    if not conversacion:
        return jsonify(error="conversación no encontrada"), 404

    cuenta = get_cuenta_by_id(conversacion["cuenta_id"])
    contenido_bytes = archivo.read()
    mime_type = archivo.mimetype or "application/octet-stream"
    if mime_type.startswith("image/"):
        tipo = "image"
    elif mime_type.startswith("audio/"):
        tipo = "audio"
    elif mime_type.startswith("video/"):
        tipo = "video"
    else:
        tipo = "document"

    media_id = subir_media(cuenta, contenido_bytes, mime_type, archivo.filename or "archivo")
    wa_id = enviar_media(cuenta, conversacion["telefono"], media_id, tipo)
    registrar_mensaje_con_media(
        conversacion_id, "saliente", f"[{tipo}]", tipo, contenido_bytes, mime_type, wa_message_id=wa_id
    )

    messages = get_historial(conversacion["cuenta_id"], conversacion["telefono"])
    add_assistant_message(messages, f"[{tipo} enviado desde el panel]")
    guardar_historial(conversacion["cuenta_id"], conversacion["telefono"], messages)

    return jsonify(status="ok")
