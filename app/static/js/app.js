// Capture textarea: auto-grow + Enter to submit, Shift+Enter for new line
document.addEventListener("keydown", function (e) {
  if (e.target.tagName !== "TEXTAREA" || !e.target.closest(".capture-form")) return;
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    e.target.closest("form").requestSubmit();
  }
});
document.addEventListener("input", function (e) {
  if (e.target.tagName !== "TEXTAREA") return;
  if (!e.target.closest(".capture-form") && !e.target.classList.contains("capture-form-grow")) return;
  e.target.style.height = "auto";
  e.target.style.height = e.target.scrollHeight + "px";
});
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("textarea.capture-form-grow").forEach(function (el) {
    if (el.value) { el.style.height = "auto"; el.style.height = el.scrollHeight + "px"; }
  });
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
