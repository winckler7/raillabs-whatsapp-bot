const state = {
    cuentaId: null,
    conversaciones: [],
    conversacionActiva: null,
    ultimoMensajeId: null,
    filtro: "",
};

async function api(url, opts) {
    const res = await fetch(url, {
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        ...opts,
    });
    if (res.status === 401) {
        window.location.href = "/panel/login";
        return null;
    }
    if (!res.ok) {
        console.error("Error en", url, res.status);
        return null;
    }
    return res.json();
}

function formatHora(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(texto) {
    const div = document.createElement("div");
    div.textContent = texto;
    return div.innerHTML;
}

async function cargarCuentas() {
    const cuentas = await api("/panel/api/cuentas");
    if (!cuentas) return;
    const selector = document.getElementById("selector-cuenta");
    selector.innerHTML = cuentas
        .map((c) => `<option value="${c.id}">${escapeHtml(c.nombre_cliente)}</option>`)
        .join("");
    if (cuentas.length > 0) {
        state.cuentaId = cuentas[0].id;
        await cargarConversaciones();
    }
}

async function cargarConversaciones() {
    if (!state.cuentaId) return;
    const conversaciones = await api(`/panel/api/conversaciones?cuenta_id=${state.cuentaId}`);
    if (!conversaciones) return;
    state.conversaciones = conversaciones;
    renderListaConversaciones();
}

function renderListaConversaciones() {
    const lista = document.getElementById("lista-conversaciones");
    const filtro = state.filtro.toLowerCase();
    const filtradas = state.conversaciones.filter(
        (c) =>
            c.telefono.toLowerCase().includes(filtro) ||
            (c.nombre && c.nombre.toLowerCase().includes(filtro))
    );

    lista.innerHTML = filtradas
        .map((c) => {
            const activo = state.conversacionActiva === c.id ? "activo" : "";
            const preview = c.ultimo_texto ? escapeHtml(c.ultimo_texto) : "";
            const badge = c.no_leidos > 0 ? `<span class="conv-badge">${c.no_leidos}</span>` : "";
            return `
                <li class="conv-item ${activo}" data-id="${c.id}">
                    <div class="conv-main">
                        <div class="conv-nombre">${escapeHtml(c.nombre || c.telefono)}</div>
                        <div class="conv-preview">${preview}</div>
                    </div>
                    <div class="conv-side">
                        <span class="conv-hora">${formatHora(c.ultimo_mensaje)}</span>
                        <span class="conv-estado ${c.estado}">${c.estado}</span>
                        ${badge}
                    </div>
                </li>
            `;
        })
        .join("");

    lista.querySelectorAll(".conv-item").forEach((item) => {
        item.addEventListener("click", () => seleccionarConversacion(parseInt(item.dataset.id, 10)));
    });
}

async function seleccionarConversacion(id) {
    state.conversacionActiva = id;
    state.ultimoMensajeId = null;
    renderListaConversaciones();

    document.getElementById("vacio").classList.add("oculto");
    document.getElementById("hilo").classList.remove("oculto");
    document.getElementById("mensajes").innerHTML = "";
    document.getElementById("panel-notas").classList.add("oculto");

    const detalle = await api(`/panel/api/conversaciones/${id}`);
    if (!detalle) return;
    state.detalleActivo = detalle;

    mostrarNombreContacto(detalle);
    document.getElementById("selector-estado").value = detalle.estado;
    document.getElementById("notas").value = detalle.notas || "";
    actualizarBotonModo(detalle.modo);

    const mensajes = await api(`/panel/api/conversaciones/${id}/mensajes`);
    if (mensajes) {
        mensajes.forEach(renderMensaje);
        if (mensajes.length > 0) {
            state.ultimoMensajeId = mensajes[mensajes.length - 1].id;
        }
        scrollAbajo();
    }

    await api(`/panel/api/conversaciones/${id}/visto`, { method: "POST" });
    await cargarConversaciones();
}

function mostrarNombreContacto(detalle) {
    document.getElementById("contacto-nombre").textContent = detalle.nombre || detalle.telefono;
    document.getElementById("contacto-nombre-input").value = detalle.nombre || "";
    document.getElementById("contacto-detalle").textContent =
        (detalle.nombre ? detalle.telefono + " · " : "") +
        "Primer contacto: " +
        new Date(detalle.primer_contacto).toLocaleDateString("es-MX");
}

function actualizarBotonModo(modo) {
    const btn = document.getElementById("btn-modo");
    btn.classList.remove("bot", "humano");
    if (modo === "humano") {
        btn.textContent = "Reactivar bot";
        btn.classList.add("humano");
    } else {
        btn.textContent = "Pausar bot";
        btn.classList.add("bot");
    }
    btn.dataset.modoActual = modo;
}

function renderMensaje(m) {
    const contenedor = document.getElementById("mensajes");
    const div = document.createElement("div");
    div.className = `burbuja ${m.direccion}`;
    div.innerHTML = `${escapeHtml(m.contenido)}<span class="hora">${formatHora(m.creado_en)}</span>`;
    contenedor.appendChild(div);
}

function scrollAbajo() {
    const contenedor = document.getElementById("mensajes");
    contenedor.scrollTop = contenedor.scrollHeight;
}

let pollEnCurso = false;

async function pollMensajesNuevos() {
    // Guard contra llamadas concurrentes -- el timer periódico y el envío
    // manual pueden disparar esto casi al mismo tiempo, y sin esto ambas
    // llamadas leen el mismo ultimoMensajeId viejo y duplican el render.
    if (!state.conversacionActiva || pollEnCurso) return;
    pollEnCurso = true;
    try {
        const url = state.ultimoMensajeId
            ? `/panel/api/conversaciones/${state.conversacionActiva}/mensajes?after_id=${state.ultimoMensajeId}`
            : `/panel/api/conversaciones/${state.conversacionActiva}/mensajes`;
        const mensajes = await api(url);
        if (!mensajes || mensajes.length === 0) return;

        mensajes.forEach(renderMensaje);
        state.ultimoMensajeId = mensajes[mensajes.length - 1].id;
        scrollAbajo();

        if (mensajes.some((m) => m.direccion === "entrante")) {
            await api(`/panel/api/conversaciones/${state.conversacionActiva}/visto`, { method: "POST" });
        }
    } finally {
        pollEnCurso = false;
    }
}

document.getElementById("selector-cuenta").addEventListener("change", (e) => {
    state.cuentaId = parseInt(e.target.value, 10);
    state.conversacionActiva = null;
    document.getElementById("hilo").classList.add("oculto");
    document.getElementById("vacio").classList.remove("oculto");
    cargarConversaciones();
});

document.getElementById("buscador").addEventListener("input", (e) => {
    state.filtro = e.target.value;
    renderListaConversaciones();
});

document.getElementById("selector-estado").addEventListener("change", async (e) => {
    if (!state.conversacionActiva) return;
    await api(`/panel/api/conversaciones/${state.conversacionActiva}/estado`, {
        method: "POST",
        body: JSON.stringify({ estado: e.target.value }),
    });
    cargarConversaciones();
});

document.getElementById("btn-modo").addEventListener("click", async (e) => {
    if (!state.conversacionActiva) return;
    const nuevoModo = e.target.dataset.modoActual === "humano" ? "bot" : "humano";
    await api(`/panel/api/conversaciones/${state.conversacionActiva}/modo`, {
        method: "POST",
        body: JSON.stringify({ modo: nuevoModo }),
    });
    actualizarBotonModo(nuevoModo);
});

document.getElementById("btn-editar-nombre").addEventListener("click", () => {
    document.getElementById("contacto-nombre").classList.add("oculto");
    const input = document.getElementById("contacto-nombre-input");
    input.classList.remove("oculto");
    input.focus();
    input.select();
});

async function guardarNombreContacto() {
    if (!state.conversacionActiva) return;
    const input = document.getElementById("contacto-nombre-input");
    const nombre = input.value.trim();
    input.classList.add("oculto");
    document.getElementById("contacto-nombre").classList.remove("oculto");

    await api(`/panel/api/conversaciones/${state.conversacionActiva}/nombre`, {
        method: "POST",
        body: JSON.stringify({ nombre }),
    });
    state.detalleActivo.nombre = nombre || null;
    mostrarNombreContacto(state.detalleActivo);
    cargarConversaciones();
}

document.getElementById("contacto-nombre-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        guardarNombreContacto();
    }
});

document.getElementById("contacto-nombre-input").addEventListener("blur", guardarNombreContacto);

document.getElementById("btn-notas-toggle").addEventListener("click", () => {
    document.getElementById("panel-notas").classList.toggle("oculto");
});

document.getElementById("btn-guardar-notas").addEventListener("click", async () => {
    if (!state.conversacionActiva) return;
    const notas = document.getElementById("notas").value;
    await api(`/panel/api/conversaciones/${state.conversacionActiva}/notas`, {
        method: "POST",
        body: JSON.stringify({ notas }),
    });
});

document.getElementById("form-responder").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.conversacionActiva) return;
    const textarea = document.getElementById("texto-respuesta");
    const texto = textarea.value.trim();
    if (!texto) return;
    textarea.value = "";
    const resultado = await api(`/panel/api/conversaciones/${state.conversacionActiva}/responder`, {
        method: "POST",
        body: JSON.stringify({ texto }),
    });
    if (resultado) {
        await pollMensajesNuevos();
        cargarConversaciones();
    }
});

document.getElementById("texto-respuesta").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        document.getElementById("form-responder").requestSubmit();
    }
});

cargarCuentas();
setInterval(cargarConversaciones, 4000);
setInterval(pollMensajesNuevos, 3000);
