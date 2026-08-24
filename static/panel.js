const state = {
    cuentaId: null,
    conversaciones: [],
    conversacionActiva: null,
    detalleActivo: null,
    ultimoMensajeId: null,
    filtro: "",
    buzon: "bandeja",
    etiquetas: [],
    filtroEtiqueta: null,
    plantillas: [],
    ticksConocidos: {},
};

let modoGestionPlantillas = false;

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
        await cargarEtiquetasYPlantillas();
    }
}

async function cargarEtiquetasYPlantillas() {
    const [etiquetas, plantillas] = await Promise.all([
        api(`/panel/api/etiquetas?cuenta_id=${state.cuentaId}`),
        api(`/panel/api/plantillas?cuenta_id=${state.cuentaId}`),
    ]);
    state.etiquetas = etiquetas || [];
    state.plantillas = plantillas || [];
    renderFiltroEtiquetas();
    renderPlantillasChips();
}

async function cargarConversaciones() {
    if (!state.cuentaId) return;
    const archivadas = state.buzon === "archivadas" ? "&archivadas=1" : "";
    const conversaciones = await api(
        `/panel/api/conversaciones?cuenta_id=${state.cuentaId}${archivadas}`
    );
    if (!conversaciones) return;
    state.conversaciones = conversaciones;
    renderListaConversaciones();
}

function renderFiltroEtiquetas() {
    const cont = document.getElementById("filtro-etiquetas");
    const todas = `<button type="button" class="chip-etiqueta ${state.filtroEtiqueta ? "inactivo" : ""}" data-id="">Todas</button>`;
    const chips = state.etiquetas
        .map((e) => {
            const activo = state.filtroEtiqueta === e.id;
            const estilo = activo ? `style="background:${e.color}"` : "";
            return `<button type="button" class="chip-etiqueta ${activo ? "" : "inactivo"}" data-id="${e.id}" ${estilo}>${escapeHtml(e.nombre)}</button>`;
        })
        .join("");
    cont.innerHTML = todas + chips;
    cont.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
            state.filtroEtiqueta = btn.dataset.id ? parseInt(btn.dataset.id, 10) : null;
            renderFiltroEtiquetas();
            renderListaConversaciones();
        });
    });
}

function renderListaConversaciones() {
    const lista = document.getElementById("lista-conversaciones");
    const filtro = state.filtro.toLowerCase();
    let filtradas = state.conversaciones.filter(
        (c) =>
            c.telefono.toLowerCase().includes(filtro) ||
            (c.nombre && c.nombre.toLowerCase().includes(filtro))
    );
    if (state.filtroEtiqueta) {
        filtradas = filtradas.filter((c) => (c.etiquetas || []).some((e) => e.id === state.filtroEtiqueta));
    }

    lista.innerHTML = filtradas
        .map((c) => {
            const activo = state.conversacionActiva === c.id ? "activo" : "";
            const preview = c.ultimo_texto ? escapeHtml(c.ultimo_texto) : "";
            const badge = c.no_leidos > 0 ? `<span class="conv-badge">${c.no_leidos}</span>` : "";
            const puntos = (c.etiquetas || [])
                .map((e) => `<span class="punto" style="background:${e.color}" title="${escapeHtml(e.nombre)}"></span>`)
                .join("");
            return `
                <li class="conv-item ${activo}" data-id="${c.id}">
                    <div class="conv-main">
                        <div class="conv-nombre">${escapeHtml(c.nombre || c.telefono)}</div>
                        <div class="conv-preview">${preview}</div>
                        ${puntos ? `<div class="conv-etiquetas">${puntos}</div>` : ""}
                    </div>
                    <div class="conv-side">
                        <span class="conv-hora">${formatHora(c.ultimo_mensaje)}</span>
                        <span class="conv-estado ${c.estado}">${c.estado}</span>
                        ${badge}
                        <button type="button" class="conv-archivar" data-id="${c.id}" data-archivada="${c.archivada}">${c.archivada ? "Desarchivar" : "Archivar"}</button>
                    </div>
                </li>
            `;
        })
        .join("");

    lista.querySelectorAll(".conv-item").forEach((item) => {
        item.addEventListener("click", (e) => {
            if (e.target.classList.contains("conv-archivar")) return;
            seleccionarConversacion(parseInt(item.dataset.id, 10));
        });
    });

    lista.querySelectorAll(".conv-archivar").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.stopPropagation();
            const id = parseInt(btn.dataset.id, 10);
            const archivada = btn.dataset.archivada !== "true";
            await api(`/panel/api/conversaciones/${id}/archivar`, {
                method: "POST",
                body: JSON.stringify({ archivada }),
            });
            if (state.conversacionActiva === id) {
                cerrarHilo();
            }
            cargarConversaciones();
        });
    });
}

function cerrarHilo() {
    state.conversacionActiva = null;
    document.getElementById("hilo").classList.add("oculto");
    document.getElementById("vacio").classList.remove("oculto");
}

async function seleccionarConversacion(id) {
    state.conversacionActiva = id;
    state.ultimoMensajeId = null;
    state.ticksConocidos = {};
    renderListaConversaciones();

    document.getElementById("vacio").classList.add("oculto");
    document.getElementById("hilo").classList.remove("oculto");
    document.getElementById("mensajes").innerHTML = "";
    document.getElementById("panel-notas").classList.add("oculto");
    document.getElementById("panel-etiquetas").classList.add("oculto");

    const detalle = await api(`/panel/api/conversaciones/${id}`);
    if (!detalle) return;
    state.detalleActivo = detalle;

    mostrarNombreContacto(detalle);
    mostrarEtiquetasHeader(detalle);
    document.getElementById("selector-estado").value = detalle.estado;
    document.getElementById("notas").value = detalle.notas || "";
    actualizarBotonModo(detalle.modo);
    actualizarBotonArchivar(detalle.archivada);

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

function mostrarEtiquetasHeader(detalle) {
    const cont = document.getElementById("etiquetas-conversacion");
    cont.innerHTML = (detalle.etiquetas || [])
        .map((e) => `<span class="chip-etiqueta" style="background:${e.color}">${escapeHtml(e.nombre)}</span>`)
        .join("");
}

function renderEtiquetasChips() {
    const cont = document.getElementById("etiquetas-chips");
    const asignadas = new Set((state.detalleActivo.etiquetas || []).map((e) => e.id));
    cont.innerHTML = state.etiquetas
        .map((e) => {
            const activo = asignadas.has(e.id);
            const estilo = activo ? `style="background:${e.color}"` : "";
            return `<button type="button" class="chip-etiqueta ${activo ? "" : "inactivo"}" data-id="${e.id}" ${estilo}>${escapeHtml(e.nombre)}</button>`;
        })
        .join("");
    cont.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => toggleEtiqueta(parseInt(btn.dataset.id, 10)));
    });
}

async function toggleEtiqueta(etiquetaId) {
    const actuales = new Set((state.detalleActivo.etiquetas || []).map((e) => e.id));
    if (actuales.has(etiquetaId)) {
        actuales.delete(etiquetaId);
    } else {
        actuales.add(etiquetaId);
    }
    await api(`/panel/api/conversaciones/${state.conversacionActiva}/etiquetas`, {
        method: "POST",
        body: JSON.stringify({ etiqueta_ids: Array.from(actuales) }),
    });
    state.detalleActivo.etiquetas = state.etiquetas.filter((e) => actuales.has(e.id));
    renderEtiquetasChips();
    mostrarEtiquetasHeader(state.detalleActivo);
    cargarConversaciones();
}

async function crearEtiquetaPrompt() {
    const nombre = prompt("Nombre de la nueva etiqueta:");
    if (!nombre) return;
    const colores = ["#00a884", "#f0ad4e", "#5bc0de", "#d9534f", "#9b59b6", "#34495e"];
    const color = colores[state.etiquetas.length % colores.length];
    const nueva = await api("/panel/api/etiquetas", {
        method: "POST",
        body: JSON.stringify({ cuenta_id: state.cuentaId, nombre, color }),
    });
    if (nueva) {
        state.etiquetas.push(nueva);
        renderFiltroEtiquetas();
        if (state.detalleActivo) renderEtiquetasChips();
    }
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

function actualizarBotonArchivar(archivada) {
    const btn = document.getElementById("btn-archivar");
    btn.textContent = archivada ? " Desarchivar" : " Archivar";
    btn.classList.toggle("archivada", archivada);
}

function iconoTicks(estado) {
    if (estado === "leido") return '<span class="tick tick-leido">✓✓</span>';
    if (estado === "entregado") return '<span class="tick">✓✓</span>';
    if (estado === "fallido") return '<span class="tick tick-fallido">!</span>';
    return '<span class="tick">✓</span>';
}

function renderMedia(m) {
    const url = `/panel/api/mensajes/${m.id}/media`;
    if (m.tipo === "image" || m.tipo === "sticker") {
        return `<img class="media-imagen" src="${url}" onclick="window.open('${url}', '_blank')">`;
    }
    if (m.tipo === "audio") {
        return `<audio class="media-audio" controls src="${url}"></audio>`;
    }
    if (m.tipo === "video") {
        return `<video class="media-video" controls src="${url}"></video>`;
    }
    return `<a class="media-documento" href="${url}" target="_blank">📄 ${escapeHtml(m.contenido)}</a>`;
}

function renderMensaje(m) {
    const contenedor = document.getElementById("mensajes");
    const div = document.createElement("div");
    div.className = `burbuja ${m.direccion}`;
    div.dataset.id = m.id;

    const mediaHtml = m.tiene_media ? renderMedia(m) : "";
    const mostrarTexto = !m.tiene_media || m.tipo !== "document";
    const texto = mostrarTexto ? escapeHtml(m.contenido) : "";
    const ticks = m.direccion === "saliente" ? `<span class="ticks">${iconoTicks(m.estado_entrega)}</span>` : "";

    div.innerHTML = `${mediaHtml}${texto}<span class="hora">${formatHora(m.creado_en)}${ticks}</span>`;
    contenedor.appendChild(div);

    if (m.direccion === "saliente") {
        state.ticksConocidos[m.id] = m.estado_entrega;
    }
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

async function pollEstadosEntrega() {
    if (!state.conversacionActiva) return;
    const estados = await api(`/panel/api/conversaciones/${state.conversacionActiva}/estados`);
    if (!estados) return;
    for (const [idStr, estado] of Object.entries(estados)) {
        const id = parseInt(idStr, 10);
        if (state.ticksConocidos[id] !== estado) {
            state.ticksConocidos[id] = estado;
            const ticksEl = document.querySelector(`.burbuja[data-id="${id}"] .ticks`);
            if (ticksEl) ticksEl.innerHTML = iconoTicks(estado);
        }
    }
}

function renderPlantillasChips() {
    const cont = document.getElementById("plantillas-chips");
    const chips = state.plantillas
        .map((p) => `<button type="button" class="chip-plantilla" data-id="${p.id}">${escapeHtml(p.texto.slice(0, 40))}</button>`)
        .join("");
    const nuevaBtn = `<button type="button" class="chip-plantilla" id="btn-nueva-plantilla">+ Nueva</button>`;
    const gestionarBtn = `<button type="button" class="chip-plantilla gestionar" id="btn-gestionar-plantillas">${modoGestionPlantillas ? "Listo" : "Gestionar"}</button>`;
    cont.innerHTML = chips + nuevaBtn + gestionarBtn;

    cont.querySelectorAll(".chip-plantilla[data-id]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const id = parseInt(btn.dataset.id, 10);
            if (modoGestionPlantillas) {
                eliminarPlantilla(id);
            } else {
                const plantilla = state.plantillas.find((p) => p.id === id);
                const textarea = document.getElementById("texto-respuesta");
                textarea.value = textarea.value ? textarea.value + " " + plantilla.texto : plantilla.texto;
                textarea.focus();
            }
        });
    });
    document.getElementById("btn-nueva-plantilla").addEventListener("click", crearPlantillaPrompt);
    document.getElementById("btn-gestionar-plantillas").addEventListener("click", () => {
        modoGestionPlantillas = !modoGestionPlantillas;
        renderPlantillasChips();
    });
}

async function crearPlantillaPrompt() {
    const texto = prompt("Texto de la respuesta rápida:");
    if (!texto) return;
    const nueva = await api("/panel/api/plantillas", {
        method: "POST",
        body: JSON.stringify({ cuenta_id: state.cuentaId, texto }),
    });
    if (nueva) {
        state.plantillas.push(nueva);
        renderPlantillasChips();
    }
}

async function eliminarPlantilla(id) {
    await api(`/panel/api/plantillas/${id}`, { method: "DELETE" });
    state.plantillas = state.plantillas.filter((p) => p.id !== id);
    renderPlantillasChips();
}

document.querySelectorAll(".tab-buzon").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-buzon").forEach((b) => b.classList.remove("activo"));
        btn.classList.add("activo");
        state.buzon = btn.dataset.buzon;
        cerrarHilo();
        cargarConversaciones();
    });
});

document.getElementById("selector-cuenta").addEventListener("change", (e) => {
    state.cuentaId = parseInt(e.target.value, 10);
    state.filtroEtiqueta = null;
    cerrarHilo();
    cargarConversaciones();
    cargarEtiquetasYPlantillas();
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

document.getElementById("btn-archivar").addEventListener("click", async () => {
    if (!state.conversacionActiva) return;
    const nuevaArchivada = !state.detalleActivo.archivada;
    await api(`/panel/api/conversaciones/${state.conversacionActiva}/archivar`, {
        method: "POST",
        body: JSON.stringify({ archivada: nuevaArchivada }),
    });
    state.detalleActivo.archivada = nuevaArchivada;
    cerrarHilo();
    cargarConversaciones();
});

document.getElementById("btn-etiquetas-toggle").addEventListener("click", () => {
    document.getElementById("panel-notas").classList.add("oculto");
    document.getElementById("panel-etiquetas").classList.toggle("oculto");
    renderEtiquetasChips();
});

document.getElementById("btn-nueva-etiqueta").addEventListener("click", crearEtiquetaPrompt);

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
    document.getElementById("panel-etiquetas").classList.add("oculto");
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

document.getElementById("btn-adjuntar").addEventListener("click", () => {
    if (!state.conversacionActiva) return;
    document.getElementById("input-archivo").click();
});

document.getElementById("input-archivo").addEventListener("change", async (e) => {
    if (!state.conversacionActiva) return;
    const archivo = e.target.files[0];
    e.target.value = "";
    if (!archivo) return;

    const formData = new FormData();
    formData.append("archivo", archivo);
    const res = await fetch(`/panel/api/conversaciones/${state.conversacionActiva}/responder-media`, {
        method: "POST",
        credentials: "same-origin",
        body: formData,
    });
    if (res.ok) {
        await pollMensajesNuevos();
        cargarConversaciones();
    } else {
        alert("No se pudo enviar el archivo.");
    }
});

cargarCuentas();
setInterval(cargarConversaciones, 4000);
setInterval(pollMensajesNuevos, 3000);
setInterval(pollEstadosEntrega, 4000);
