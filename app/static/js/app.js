// Textareas que crecen con el texto en lugar de scrollear.

function wdigdGrow(el) {
  // El placeholder no cuenta para scrollHeight: si el campo está vacío se mide con
  // el placeholder puesto, para que un placeholder de dos líneas no quede cortado.
  var placeholding = !el.value && el.placeholder;
  if (placeholding) el.value = el.placeholder;
  el.style.height = "auto";
  // scrollHeight no incluye los bordes: con box-sizing: border-box hay que sumarlos
  // o queda un scroll de un par de píxeles.
  var cs = getComputedStyle(el);
  var extra =
    cs.boxSizing === "border-box"
      ? parseFloat(cs.borderTopWidth) + parseFloat(cs.borderBottomWidth)
      : 0;
  el.style.height = el.scrollHeight + extra + "px";
  if (placeholding) el.value = "";
}

document.addEventListener("input", function (e) {
  if (e.target.tagName === "TEXTAREA" && e.target.classList.contains("js-autogrow")) {
    wdigdGrow(e.target);
  }
});
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("textarea.js-autogrow").forEach(wdigdGrow);
});
window.addEventListener("resize", function () {
  document.querySelectorAll("textarea.js-autogrow").forEach(wdigdGrow);
});

// Auto-formateo de listas mientras se escribe (journal semanal y nota del día).
//
// "* " o "- " al principio de una línea se vuelven "• " en el acto. Enter continúa
// la lista (viñeta o número siguiente) y Enter sobre un ítem vacío la corta.
// Lo que se guarda es texto plano: el filtro `narrative` ya entiende •, *, - y "1.".

var wdigdAutolistBusy = false;

// Reemplaza un rango usando execCommand para no romper el undo del navegador.
function wdigdReplaceRange(el, start, end, text) {
  el.focus();
  el.setSelectionRange(start, end);
  var ok = false;
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
  var el = e.target;
  if (wdigdAutolistBusy) return null;
  if (el.tagName !== "TEXTAREA" || !el.classList.contains("js-autolist")) return null;
  if (el.selectionStart !== el.selectionEnd) return null;
  return el;
}

function wdigdLineStart(value, pos) {
  return value.lastIndexOf("\n", pos - 1) + 1;
}

document.addEventListener("input", function (e) {
  var el = wdigdAutolistTarget(e);
  if (!el) return;
  var pos = el.selectionStart;
  var start = wdigdLineStart(el.value, pos);
  var m = /^([ \t]*)[*-] $/.exec(el.value.slice(start, pos));
  if (!m) return;
  wdigdAutolistBusy = true;
  wdigdReplaceRange(el, start + m[1].length, pos, "• ");
  wdigdAutolistBusy = false;
});

document.addEventListener("keydown", function (e) {
  if (e.key !== "Enter" || e.shiftKey || e.ctrlKey || e.metaKey || e.altKey) return;
  var el = wdigdAutolistTarget(e);
  if (!el) return;

  var pos = el.selectionStart;
  var start = wdigdLineStart(el.value, pos);
  var end = el.value.indexOf("\n", pos);
  if (end === -1) end = el.value.length;
  var line = el.value.slice(start, end);

  var ul = /^([ \t]*)[•*-][ \t]+/.exec(line);
  var ol = ul ? null : /^([ \t]*)(\d+)([.)])[ \t]+/.exec(line);
  if (!ul && !ol) return;

  e.preventDefault();
  wdigdAutolistBusy = true;
  var marker = (ul || ol)[0];
  if (!line.slice(marker.length).trim()) {
    // Ítem vacío: se sale de la lista en vez de agregar otra viñeta.
    wdigdReplaceRange(el, start, end, "");
  } else {
    var next = ul
      ? ul[1] + "• "
      : ol[1] + (parseInt(ol[2], 10) + 1) + ol[3] + " ";
    wdigdReplaceRange(el, pos, pos, "\n" + next);
  }
  wdigdAutolistBusy = false;
});

// El H1 de /week es el nombre de la semana. Sin nombre muestra el rango de fechas
// como placeholder; con nombre, el rango baja a la línea de abajo.

function wdigdWeekTitle(el) {
  var sub = document.querySelector(".wk-title-sub");
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

// Toggle dark/light mode

function wdigdToggleTheme() {
  var current = document.documentElement.style.colorScheme;
  var next = current === "dark" ? "light" : current === "light" ? "" : "dark";
  document.documentElement.style.colorScheme = next;
  if (next) {
    document.cookie = "theme=" + next + ";path=/;max-age=31536000;SameSite=Lax";
  } else {
    document.cookie = "theme=;path=/;max-age=0";
  }
}

// Prioridades de la semana que viene: chips.
//
// El almacenamiento sigue siendo texto, una prioridad por línea; acá se arma esa
// lista a partir de los chips y se manda entera en cada cambio.

function wdigdSavePriorities(editor) {
  const chips = editor.querySelectorAll(".chip-edit");
  const text = Array.from(chips).map(function (c) { return c.dataset.text; }).join("\n");
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
    if (existing.some(function (c) { return c.dataset.text.toLowerCase() === text.toLowerCase(); })) return;

    const chip = document.createElement("span");
    chip.className = "chip-prio chip-edit";
    chip.dataset.text = text;
    chip.textContent = text;
    const x = document.createElement("button");
    x.type = "button";
    x.className = "chip-x";
    x.title = "Quitar";
    x.setAttribute("onclick", "wdigdRemovePriority(this)");
    x.textContent = "×";
    chip.appendChild(x);
    chips.appendChild(chip);
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

// Alinear un bullet con una prioridad de la semana.
//
// Cada tap cicla la etiqueta EN EL LUGAR (el bullet no se mueve) mostrando la
// prioridad elegida; recién 1.7s después del último tap se confirma contra el
// servidor y el bullet se reagrupa. Así hay tiempo de leer con qué prioridad
// quedó y de seguir ciclando hasta la correcta.

const WDIGD_ALIGN_DELAY = 1700;

function wdigdCycleAlign(btn) {
  const container = btn.closest("[data-priorities]");
  let priorities = [];
  try {
    priorities = JSON.parse(container ? container.dataset.priorities : "[]");
  } catch (e) {
    priorities = [];
  }
  if (!priorities.length) return;

  const current = btn.dataset.label || "";
  let next;
  if (!current) {
    next = priorities[0];
  } else {
    const i = priorities.indexOf(current);
    next = i >= 0 && i + 1 < priorities.length ? priorities[i + 1] : "";
  }

  btn.dataset.label = next;
  btn.textContent = next || "alinear con prioridades";
  btn.classList.toggle("has", !!next);
  btn.classList.add("pending");

  clearTimeout(btn._alignTimer);
  btn._alignTimer = setTimeout(function () {
    const sel = btn.dataset.alignTarget || "";
    const target = sel.indexOf("closest ") === 0 ? btn.closest(sel.slice(8)) : sel;
    if (!target || typeof htmx === "undefined") return;
    htmx.ajax("POST", btn.dataset.alignUrl, {
      target: target,
      swap: "outerHTML",
      values: { label: btn.dataset.label },
    });
  }, WDIGD_ALIGN_DELAY);
}
