// Progressive enhancement de wdigd. Todo lo de acá es opcional: sin JS la app
// sigue funcionando por formularios y HTMX.
//
// Las funciones con prefijo `wdigd` se llaman desde atributos inline de los
// templates. Son inline a propósito: los fragmentos que HTMX reemplaza pierden
// los listeners, y en el bloque 1 de /week hay que frenar la propagación del
// click ANTES de que lo tome el hx-post de la fila (un listener delegado en
// document correría después).

// — Textareas que crecen con el texto en lugar de scrollear —

function wdigdGrow(el) {
  // El placeholder no cuenta para scrollHeight: si el campo está vacío se mide con
  // el placeholder puesto, para que un placeholder de dos líneas no quede cortado.
  const placeholding = !el.value && el.placeholder;
  if (placeholding) el.value = el.placeholder;
  el.style.height = "auto";
  // scrollHeight no incluye los bordes: con box-sizing: border-box hay que sumarlos
  // o queda un scroll de un par de píxeles.
  const cs = getComputedStyle(el);
  const extra =
    cs.boxSizing === "border-box"
      ? parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth)
      : 0;
  el.style.height = el.scrollHeight + extra + "px";
  if (placeholding) el.value = "";
}

function wdigdGrowAll() {
  document.querySelectorAll("textarea.js-autogrow").forEach(wdigdGrow);
}

document.addEventListener("input", function (e) {
  if (e.target.tagName === "TEXTAREA" && e.target.classList.contains("js-autogrow")) {
    wdigdGrow(e.target);
  }
});
document.addEventListener("DOMContentLoaded", wdigdGrowAll);
window.addEventListener("resize", wdigdGrowAll);

// — Auto-formateo de listas mientras se escribe (journal semanal y nota del día) —
//
// "* " o "- " al principio de una línea se vuelven "• " en el acto. Enter continúa
// la lista (viñeta o número siguiente) y Enter sobre un ítem vacío la corta.
// Lo que se guarda es texto plano: el filtro `narrative` ya entiende •, *, - y "1.".

let wdigdAutolistBusy = false;

// Reemplaza un rango usando execCommand para no romper el undo del navegador.
function wdigdReplaceRange(el, start, end, text) {
  el.focus();
  el.setSelectionRange(start, end);
  let ok = false;
  try {
    ok = text
      ? document.execCommand("insertText", false, text)
      : start !== end && document.execCommand("delete");
  } catch (err) {
    ok = false;
  }
  if (!ok) {
    el.setRangeText(text, start, end, "end");
    el.dispatchEvent(new Event("input", { bubbles: true }));
  }
}

function wdigdAutolistTarget(e) {
  const el = e.target;
  if (wdigdAutolistBusy) return null;
  if (el.tagName !== "TEXTAREA" || !el.classList.contains("js-autolist")) return null;
  if (el.selectionStart !== el.selectionEnd) return null;
  return el;
}

function wdigdLineStart(value, pos) {
  return value.lastIndexOf("\n", pos - 1) + 1;
}

document.addEventListener("input", function (e) {
  const el = wdigdAutolistTarget(e);
  if (!el) return;
  const pos = el.selectionStart;
  const start = wdigdLineStart(el.value, pos);
  const dash = /^([ \t]*)[*-] $/.exec(el.value.slice(start, pos));
  if (!dash) return;
  wdigdAutolistBusy = true;
  wdigdReplaceRange(el, start + dash[1].length, pos, "• ");
  wdigdAutolistBusy = false;
});

document.addEventListener("keydown", function (e) {
  if (e.key !== "Enter" || e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
  const el = wdigdAutolistTarget(e);
  if (!el) return;

  const pos = el.selectionStart;
  const start = wdigdLineStart(el.value, pos);
  let end = el.value.indexOf("\n", pos);
  if (end === -1) end = el.value.length;
  const line = el.value.slice(start, end);

  const ul = /^([ \t]*)[•*-][ \t]+/.exec(line);
  const ol = ul ? null : /^([ \t]*)(\d+)([.)])[ \t]+/.exec(line);
  if (!ul && !ol) return;

  e.preventDefault();
  wdigdAutolistBusy = true;
  const marker = (ul || ol)[0];
  if (!line.slice(marker.length).trim()) {
    // Ítem vacío: se sale de la lista en vez de agregar otra viñeta.
    wdigdReplaceRange(el, start, end, "");
  } else {
    const next = ul ? ul[1] + "• " : ol[1] + (parseInt(ol[2], 10) + 1) + ol[3] + " ";
    wdigdReplaceRange(el, pos, pos, "\n" + next);
  }
  wdigdAutolistBusy = false;
});

// — Título de /week —
//
// El H1 es el nombre de la semana. Sin nombre muestra el rango de fechas como
// placeholder; con nombre, el rango baja a la línea de abajo.

function wdigdWeekTitle(el) {
  const sub = document.querySelector(".wk-title-sub");
  if (sub) sub.hidden = !el.value.trim();
}

// Es un textarea sólo para que envuelva: Enter cierra la edición, no agrega líneas.
document.addEventListener("keydown", function (e) {
  if (!e.target.classList || !e.target.classList.contains("wk-title-input")) return;
  if (e.key === "Enter") {
    e.preventDefault();
    e.target.blur();
  }
});

// — Tema claro / oscuro —
//
// Cicla oscuro → claro → el del sistema. base.html lee la cookie antes del primer
// pintado para que no haya parpadeo.

const WDIGD_THEME_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

function wdigdToggleTheme() {
  const current = document.documentElement.style.colorScheme;
  const next = current === "dark" ? "light" : current === "light" ? "" : "dark";
  document.documentElement.style.colorScheme = next;
  if (next) {
    document.cookie =
      "theme=" + next + ";path=/;max-age=" + WDIGD_THEME_COOKIE_MAX_AGE + ";SameSite=Lax";
  } else {
    document.cookie = "theme=;path=/;max-age=0";
  }
}

// — Prioridades de la semana que viene: chips —
//
// El almacenamiento sigue siendo texto, una prioridad por línea; acá se arma esa
// lista a partir de los chips y se manda entera en cada cambio.

function wdigdSavePriorities(editor) {
  const chips = editor.querySelectorAll(".chip-edit");
  const text = Array.from(chips)
    .map(function (chip) { return chip.dataset.text; })
    .join("\n");
  if (typeof htmx === "undefined") return;
  htmx.ajax("PATCH", editor.dataset.url, { values: { priorities: text }, swap: "none" });
}

function wdigdRemovePriority(btn) {
  const editor = btn.closest(".prio-editor");
  btn.closest(".chip-edit").remove();
  wdigdSavePriorities(editor);
  const input = editor.querySelector(".prio-input");
  if (input) input.focus();
}

function wdigdPriorityChip(text) {
  const chip = document.createElement("span");
  chip.className = "chip-prio chip-edit";
  chip.dataset.text = text;
  chip.textContent = text;

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "chip-x";
  remove.title = "Quitar";
  remove.textContent = "×";

  chip.appendChild(remove);
  return chip;
}

// Delegado: sirve igual para los chips que vienen del servidor y para los recién creados.
document.addEventListener("click", function (e) {
  const remove = e.target.closest && e.target.closest(".chip-x");
  if (remove) wdigdRemovePriority(remove);
});

function wdigdPriorityKey(e, input) {
  const editor = input.closest(".prio-editor");
  const chips = editor.querySelector(".prio-chips");

  if (e.key === "Enter") {
    e.preventDefault();
    const text = input.value.trim().replace(/^[-•*]\s*/, "").trim();
    input.value = "";
    if (!text) return;
    const existing = Array.from(chips.querySelectorAll(".chip-edit"));
    // Dos prioridades con el mismo texto vuelven ambiguo el botón "alinear".
    const repeated = existing.some(function (chip) {
      return chip.dataset.text.toLowerCase() === text.toLowerCase();
    });
    if (repeated) return;

    chips.appendChild(wdigdPriorityChip(text));
    wdigdSavePriorities(editor);
    return;
  }

  if (e.key === "Backspace" && input.value === "") {
    const last = chips.querySelector(".chip-edit:last-child");
    if (!last) return;
    e.preventDefault();
    last.remove();
    wdigdSavePriorities(editor);
  }
}

// — Alinear un bullet con una prioridad de la semana —
//
// Cada tap cicla la etiqueta EN EL LUGAR (el bullet no se mueve) mostrando la
// prioridad elegida; recién 1.7s después del último tap se confirma contra el
// servidor y el bullet se reagrupa. Así hay tiempo de leer con qué prioridad
// quedó y de seguir ciclando hasta la correcta.

const WDIGD_ALIGN_DELAY = 1700;
const WDIGD_ALIGN_EMPTY_LABEL = "alinear con prioridades";

function wdigdPrioritiesOf(el) {
  const container = el.closest("[data-priorities]");
  if (!container) return [];
  try {
    return JSON.parse(container.dataset.priorities);
  } catch (err) {
    return [];
  }
}

function wdigdNextPriority(current, priorities) {
  if (!current) return priorities[0];
  const i = priorities.indexOf(current);
  return i >= 0 && i + 1 < priorities.length ? priorities[i + 1] : "";
}

function wdigdCycleAlign(btn) {
  const priorities = wdigdPrioritiesOf(btn);
  if (!priorities.length) return;

  const next = wdigdNextPriority(btn.dataset.label || "", priorities);
  btn.dataset.label = next;
  btn.textContent = next || WDIGD_ALIGN_EMPTY_LABEL;
  btn.classList.toggle("has", !!next);
  btn.classList.add("pending");

  clearTimeout(btn._alignTimer);
  btn._alignTimer = setTimeout(function () {
    const selector = btn.dataset.alignTarget || "";
    const target = selector.indexOf("closest ") === 0
      ? btn.closest(selector.slice("closest ".length))
      : selector;
    if (!target || typeof htmx === "undefined") return;
    htmx.ajax("POST", btn.dataset.alignUrl, {
      target: target,
      swap: "outerHTML",
      values: { label: btn.dataset.label },
    });
  }, WDIGD_ALIGN_DELAY);
}

// — Formularios que no se mandan dos veces —
//
// "Cerrar el día" y "Reabrir" son POST planos: dos clicks seguidos mandan dos
// pedidos que compiten por crear la misma nota. El backend ya lo tolera; esto
// evita el pedido de más y el parpadeo de dos redirects.

function wdigdSubmitButtons(form) {
  return form.querySelectorAll("button[type=submit]");
}

document.addEventListener("submit", function (e) {
  const form = e.target;
  if (!form.classList || !form.classList.contains("js-once")) return;
  if (form.dataset.submitted) {
    e.preventDefault();
    return;
  }
  form.dataset.submitted = "1";
  // Deshabilitar recién en el próximo tick: un botón disabled durante el evento
  // submit puede quedar afuera de los datos enviados.
  setTimeout(function () {
    wdigdSubmitButtons(form).forEach(function (btn) { btn.disabled = true; });
  }, 0);
});

// Al volver con el botón "atrás" el navegador puede restaurar la página tal cual
// quedó, con el botón deshabilitado.
window.addEventListener("pageshow", function (e) {
  if (!e.persisted) return;
  document.querySelectorAll("form.js-once").forEach(function (form) {
    delete form.dataset.submitted;
    wdigdSubmitButtons(form).forEach(function (btn) { btn.disabled = false; });
  });
});

// — Cambio de día con la pestaña abierta —
//
// /today se renderiza para un día concreto: si pasa la medianoche (o la pestaña
// vuelve del fondo otro día), se recarga sola para no capturar en el día de ayer.

const WDIGD_ROLLOVER_MARGIN = 500;

function wdigdWatchDayRollover() {
  const marker = document.querySelector(".js-day-rollover");
  if (!marker) return;
  const rendered = marker.dataset.date;

  function check() {
    // "sv-SE" da el formato ISO (2026-07-26) en la timezone del navegador.
    if (new Date().toLocaleDateString("sv-SE") !== rendered) location.reload();
  }

  const tomorrow = new Date(rendered + "T00:00:00");
  tomorrow.setDate(tomorrow.getDate() + 1);
  const ms = tomorrow - Date.now();
  if (ms > 0) setTimeout(check, ms + WDIGD_ROLLOVER_MARGIN);
  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) check();
  });
}

document.addEventListener("DOMContentLoaded", wdigdWatchDayRollover);
