// 世界遺産グローブ: Phase1 - 地球儀に点を表示する

const CATEGORY_COLOR = {
  Cultural: "#f4c95d", // 文化遺産: 金色系
  Natural: "#6fd08c",  // 自然遺産: 緑系
  Mixed: "#5fb4ef",    // 複合遺産: 青系
};
const DANGER_COLOR = "#ef5350";

const prefersReducedMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)"
).matches;

function pointColor(d) {
  return CATEGORY_COLOR[d.category] || "#cccccc";
}

async function loadHeritageData() {
  const res = await fetch(`${ROOT}data/heritage.json`);
  if (!res.ok) {
    throw new Error(S.fetchError(res.status));
  }
  return res.json();
}

// 訪問記録: localStorage(キー whg_visited)にidの配列として保存する
const VISITED_KEY = "whg_visited";

function createVisitedStore() {
  let ids;
  try {
    ids = new Set(JSON.parse(localStorage.getItem(VISITED_KEY) || "[]"));
  } catch {
    ids = new Set();
  }
  const listeners = new Set();

  function save() {
    localStorage.setItem(VISITED_KEY, JSON.stringify([...ids]));
    listeners.forEach((fn) => fn());
  }

  return {
    has: (id) => ids.has(id),
    toggle(id) {
      if (ids.has(id)) {
        ids.delete(id);
      } else {
        ids.add(id);
      }
      save();
    },
    count: () => ids.size,
    idSet: ids,
    onChange: (fn) => listeners.add(fn),
  };
}

function initInfoCard(visitedStore) {
  const card = document.getElementById("info-card");
  const backdrop = document.getElementById("card-backdrop");
  const closeBtn = document.getElementById("card-close");
  const badgeEl = document.getElementById("card-badge");
  const categoryEl = document.getElementById("card-category");
  const nameEl = document.getElementById("card-name");
  const metaEl = document.getElementById("card-meta");
  const descriptionEl = document.getElementById("card-description");
  const officialLink = document.getElementById("card-official-link");
  const youtubeLink = document.getElementById("card-youtube-link");
  const visitedToggle = document.getElementById("card-visited-toggle");

  let currentSite = null;

  function refreshVisitedButton() {
    if (!currentSite) return;
    const visited = visitedStore.has(currentSite.id);
    visitedToggle.textContent = visited ? S.visited : S.markVisited;
    visitedToggle.classList.toggle("active", visited);
  }

  function close() {
    card.classList.remove("open");
    backdrop.classList.remove("open");
    card.setAttribute("aria-hidden", "true");
  }

  function show(site, { badge = false } = {}) {
    currentSite = site;
    const categoryLabel = S.categoryLabel[site.category] || site.category;
    categoryEl.textContent = site.danger
      ? S.dangerCategoryLabel(categoryLabel)
      : categoryLabel;
    nameEl.textContent = pickName(site);
    metaEl.textContent = S.meta(pickCountry(site), site.year);
    descriptionEl.textContent = pickDescription(site);
    officialLink.href = site.url;
    youtubeLink.href = site.youtube_search_url;
    badgeEl.hidden = !badge;
    refreshVisitedButton();

    card.setAttribute("aria-hidden", "false");
    card.classList.add("open");
    backdrop.classList.add("open");
  }

  closeBtn.addEventListener("click", close);
  backdrop.addEventListener("click", close);
  visitedToggle.addEventListener("click", () => {
    if (!currentSite) return;
    visitedStore.toggle(currentSite.id);
    refreshVisitedButton();
  });

  return { show, close };
}

// ヘッダーの達成率表示。タップすると訪問済み一覧を開く
function initVisitedCounter(visitedStore, total, openList) {
  const countEl = document.getElementById("visited-count");
  const totalEl = document.getElementById("visited-total");
  const button = document.getElementById("visited-counter");

  totalEl.textContent = String(total);
  function refresh() {
    countEl.textContent = String(visitedStore.count());
  }
  refresh();
  visitedStore.onChange(refresh);

  button.addEventListener("click", openList);
}

// 訪問済み一覧のボトムシート
function initVisitedList(visitedStore, data, infoCard) {
  const sheet = document.getElementById("visited-list");
  const backdrop = document.getElementById("visited-backdrop");
  const closeBtn = document.getElementById("visited-close");
  const itemsEl = document.getElementById("visited-items");
  const emptyEl = document.getElementById("visited-empty");
  const byId = new Map(data.map((d) => [d.id, d]));

  function close() {
    sheet.classList.remove("open");
    backdrop.classList.remove("open");
    sheet.setAttribute("aria-hidden", "true");
  }

  function open() {
    const visitedSites = [...visitedStore.idSet]
      .map((id) => byId.get(id))
      .filter(Boolean);

    itemsEl.innerHTML = "";
    emptyEl.hidden = visitedSites.length > 0;

    visitedSites.forEach((site) => {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "visited-item";
      btn.innerHTML = `${pickName(site)}<span class="visited-item-country">${S.meta(pickCountry(site), site.year)}</span>`;
      btn.addEventListener("click", () => {
        close();
        infoCard.show(site);
      });
      li.appendChild(btn);
      itemsEl.appendChild(li);
    });

    sheet.setAttribute("aria-hidden", "false");
    sheet.classList.add("open");
    backdrop.classList.add("open");
  }

  closeBtn.addEventListener("click", close);
  backdrop.addEventListener("click", close);

  return { open, close };
}

// 日付をシードに毎日同じ「今日の世界遺産」を選ぶ
function pickTodaysSite(data) {
  const now = new Date();
  const seed = `${now.getFullYear()}-${now.getMonth() + 1}-${now.getDate()}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return data[hash % data.length];
}

// Globe.gl の onPointClick は内部で「ドラッグ中判定」が付いており、
// マウス種別のポインタでは1px でも動くと「ドラッグ」とみなされてタップが無視されてしまう
// (指のわずかな動きが起きるタッチ操作でも同様に起こりうる)。
// そのため、タップ判定と当たり判定を自前で実装して回避する。
function initTapToOpen(world, infoCard) {
  const canvas = world.renderer().domElement;
  const DRAG_THRESHOLD_PX = 8;
  const HIT_RADIUS_PX = 22;
  let downPos = null;

  function pointMeshes() {
    const meshes = [];
    world.scene().traverse((obj) => {
      if (obj.isMesh && obj.__globeObjType === "point" && obj.__data) {
        meshes.push(obj);
      }
    });
    return meshes;
  }

  function findHit(clientX, clientY) {
    const camera = world.camera();
    const Vector3 = camera.position.constructor;
    const rect = canvas.getBoundingClientRect();
    const cameraWorldPos = camera.getWorldPosition(new Vector3());
    let best = null;
    let bestDist = Infinity;
    for (const mesh of pointMeshes()) {
      const worldPos = mesh.getWorldPosition(new Vector3());
      const isFrontFacing =
        worldPos.clone().normalize().dot(cameraWorldPos.clone().normalize()) > 0;
      if (!isFrontFacing) continue;
      const proj = worldPos.clone().project(camera);
      if (proj.z > 1) continue;
      const sx = (proj.x * 0.5 + 0.5) * rect.width + rect.left;
      const sy = (-proj.y * 0.5 + 0.5) * rect.height + rect.top;
      const dist = Math.hypot(sx - clientX, sy - clientY);
      if (dist < bestDist) {
        bestDist = dist;
        best = mesh.__data;
      }
    }
    return bestDist <= HIT_RADIUS_PX ? best : null;
  }

  canvas.addEventListener("pointerdown", (e) => {
    downPos = { x: e.clientX, y: e.clientY };
  });

  canvas.addEventListener("click", (e) => {
    if (!downPos) return;
    const dist = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
    downPos = null;
    if (dist > DRAG_THRESHOLD_PX) return;
    const site = findHit(e.clientX, e.clientY);
    if (site) {
      infoCard.show(site);
      world.pointOfView({ lat: site.lat, lng: site.lng, altitude: 1.6 }, 800);
    }
  });
}

function initGlobe(container, infoCard) {
  const world = Globe()(container)
    .globeImageUrl(`${ROOT}img/earth-day.jpg`)
    .bumpImageUrl(`${ROOT}img/earth-bump.jpg`)
    .backgroundImageUrl(`${ROOT}img/night-sky.png`)
    .showAtmosphere(true)
    .atmosphereColor("#5fb4ef")
    .atmosphereAltitude(0.18)
    .pointLat("lat")
    .pointLng("lng")
    .pointColor(pointColor)
    .pointAltitude(0.01)
    .pointRadius(0.28)
    .pointResolution(6)
    .pointLabel((d) => pickName(d))
    .ringLat("lat")
    .ringLng("lng")
    .ringColor((d) =>
      d.__ringKind === "visited"
        ? (t) => `rgba(255, 255, 255, ${1 - t})`
        : (t) => `rgba(239, 83, 80, ${1 - t})`
    )
    .ringMaxRadius((d) => (d.__ringKind === "visited" ? 2.2 : 3.2))
    .ringPropagationSpeed((d) => (d.__ringKind === "visited" ? 0.35 : 0.6))
    .ringRepeatPeriod((d) => (d.__ringKind === "visited" ? 2600 : 3800));

  initTapToOpen(world, infoCard);

  const controls = world.controls();
  controls.autoRotate = !prefersReducedMotion;
  controls.autoRotateSpeed = 0.35;
  controls.addEventListener("start", () => {
    controls.autoRotate = false;
  });

  // テクスチャ解像度には限りがあるので、それ以上近づくとぼやけて荒く見える。
  // ズームできる下限を決めて、常に鮮明に見える距離までに制限する
  controls.minDistance = world.getGlobeRadius() * 1.1;

  world.onGlobeReady(() => {
    const material = world.globeMaterial();
    const maxAnisotropy = world.renderer().capabilities.getMaxAnisotropy();
    if (material.map) {
      material.map.anisotropy = maxAnisotropy;
      material.map.needsUpdate = true;
    }
    if (material.bumpMap) {
      material.bumpMap.anisotropy = maxAnisotropy;
      material.bumpMap.needsUpdate = true;
    }
    material.bumpScale = 6;
  });

  world.pointOfView({ lat: 20, lng: 20, altitude: 2.4 });

  return world;
}

// タイムライン・分類フィルタ・検索をまとめて管理し、条件に合う物件だけを地球儀に表示する
function initExplorer(world, data, visitedStore) {
  const slider = document.getElementById("timeline-slider");
  const playBtn = document.getElementById("timeline-play");
  const yearLabel = document.getElementById("timeline-year");
  const countLabel = document.getElementById("timeline-count");
  const searchInput = document.getElementById("search-input");
  const categoryButtons = Array.from(
    document.querySelectorAll(".filter-chip[data-category]")
  );
  const dangerToggle = document.getElementById("danger-toggle");

  const minYear = Math.min(...data.map((d) => d.year));
  const maxYear = Math.max(...data.map((d) => d.year));
  slider.min = String(minYear);
  slider.max = String(maxYear);
  slider.value = String(maxYear);

  const activeCategories = new Set(categoryButtons.map((b) => b.dataset.category));
  let dangerOnly = false;
  let searchText = "";
  let lastFocusedId = null;
  let timer = null;

  function computeVisible() {
    const year = Number(slider.value);
    const q = searchText.trim().toLowerCase();
    return data.filter((d) => {
      if (d.year > year) return false;
      if (!activeCategories.has(d.category)) return false;
      if (dangerOnly && !d.danger) return false;
      if (
        q &&
        !d.name.toLowerCase().includes(q) &&
        !pickName(d).toLowerCase().includes(q) &&
        !d.country.toLowerCase().includes(q) &&
        !pickCountry(d).toLowerCase().includes(q)
      ) {
        return false;
      }
      return true;
    });
  }

  function render() {
    const visible = computeVisible();
    world.pointsData(visible);

    const rings = [];
    if (!prefersReducedMotion) {
      visible.forEach((d) => {
        if (d.danger) rings.push({ ...d, __ringKind: "danger" });
        if (visitedStore.has(d.id)) rings.push({ ...d, __ringKind: "visited" });
      });
    }
    world.ringsData(rings);
    yearLabel.textContent = S.yearLabel(slider.value);
    countLabel.textContent = S.countLabel(visible.length, data.length);

    const q = searchText.trim();
    if (q && visible.length > 0) {
      const hit = visible[0];
      if (hit.id !== lastFocusedId) {
        lastFocusedId = hit.id;
        world.pointOfView({ lat: hit.lat, lng: hit.lng, altitude: 1.6 }, 800);
      }
    } else if (!q) {
      lastFocusedId = null;
    }
  }

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
    playBtn.textContent = "▶";
    playBtn.setAttribute("aria-label", S.play);
  }

  function play() {
    if (Number(slider.value) >= maxYear) {
      slider.value = String(minYear);
      render();
    }
    playBtn.textContent = "⏸";
    playBtn.setAttribute("aria-label", S.pause);
    timer = setInterval(() => {
      const next = Number(slider.value) + 1;
      if (next > maxYear) {
        stop();
        return;
      }
      slider.value = String(next);
      render();
    }, 500);
  }

  playBtn.addEventListener("click", () => {
    if (timer) {
      stop();
    } else {
      play();
    }
  });

  slider.addEventListener("input", () => {
    stop();
    render();
  });

  categoryButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const category = btn.dataset.category;
      if (activeCategories.has(category)) {
        activeCategories.delete(category);
        btn.classList.remove("active");
      } else {
        activeCategories.add(category);
        btn.classList.add("active");
      }
      render();
    });
  });

  dangerToggle.addEventListener("click", () => {
    dangerOnly = !dangerOnly;
    dangerToggle.classList.toggle("active", dangerOnly);
    render();
  });

  searchInput.addEventListener("input", () => {
    searchText = searchInput.value;
    render();
  });

  visitedStore.onChange(render);

  render();
}

function hideLoadingOverlay() {
  const overlay = document.getElementById("loading-overlay");
  if (overlay) overlay.classList.add("hidden");
}

async function main() {
  const container = document.getElementById("globe-container");
  try {
    const data = await loadHeritageData();
    const visitedStore = createVisitedStore();
    const infoCard = initInfoCard(visitedStore);
    const visitedList = initVisitedList(visitedStore, data, infoCard);
    initVisitedCounter(visitedStore, data.length, visitedList.open);

    const world = initGlobe(container, infoCard);
    initExplorer(world, data, visitedStore);
    hideLoadingOverlay();

    const todaysSite = pickTodaysSite(data);
    world.pointOfView({ lat: todaysSite.lat, lng: todaysSite.lng, altitude: 1.6 }, 1500);
    setTimeout(() => infoCard.show(todaysSite, { badge: true }), 1700);
  } catch (err) {
    console.error(err);
    hideLoadingOverlay();
    container.innerHTML = `<p style="color:#fff;padding:24px;">${S.loadError}</p>`;
  }
}

main();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register(`${ROOT}sw.js`);
  });
}
