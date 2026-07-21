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
