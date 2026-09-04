import { bindCursor, mountStatic, bindNav, paintHud, setScreen } from "./ui.js";
import { attachWorld, renderWorlds, resize } from "./scene.js";
import { tick } from "./sim.js";
import { store } from "./store.js";

bindCursor();
mountStatic();
bindNav();
setScreen("setup");

attachWorld("setup", document.getElementById("world-setup"));
attachWorld("live", document.getElementById("world-live"));
attachWorld("stress", document.getElementById("world-stress"));
resize();

function loop(now) {
  tick(now);
  const showWorld = store.screen === "setup" || store.screen === "live" || store.screen === "stress";
  if (showWorld) renderWorlds();
  paintHud();
  requestAnimationFrame(loop);
}

requestAnimationFrame(loop);
