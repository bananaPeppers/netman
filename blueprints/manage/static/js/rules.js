// Right-hand rules panel (domain block + safe mode) shared by the groups and devices pages.
// A page chooses what the panel shows with RulesPanel.select(id, name) or RulesPanel.clear().
const RulesPanel = (() => {
  const data = JSON.parse(document.getElementById("rules-data").textContent);
  const isDevice = data.target === "device";
  const idKey = isDevice ? "device_id" : "group_id";

  const nameBar = document.getElementById("rules-name-text");
  const emptyLabel = nameBar.textContent;
  const domainInput = document.getElementById("domain-input");
  const domainSaveBtn = document.getElementById("domain-save-btn");
  const domainList = document.getElementById("domain-list");
  const safeModeToggle = document.getElementById("safe-mode-toggle");

  const deletePopup = document.getElementById("delete-domain-popup");
  const deleteName = document.getElementById("delete-domain-name");
  const confirmDeleteBtn = document.getElementById("confirm-delete-domain-btn");
  const cancelDeleteBtn = document.getElementById("cancel-delete-domain-btn");

  let activeId = null;
  let pendingDelete = null; // { id, item, ownerId }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.error || "Request failed");
    return json;
  }

  function needSelection() {
    if (activeId) return false;
    alert(isDevice ? "Select a device first" : "Select or create a group first");
    return true;
  }

  function buildDomainItem(id, domain) {
    const item = document.createElement("div");
    item.className = "domain-item";

    const label = document.createElement("span");
    label.className = "domain-name";
    label.textContent = domain;

    const del = document.createElement("button");
    del.className = "domain-delete";
    del.type = "button";
    del.setAttribute("aria-label", "Remove domain");
    del.innerHTML = "&times;";
    del.addEventListener("click", () => {
      pendingDelete = { id, item, ownerId: activeId };
      deleteName.textContent = domain;
      deletePopup.classList.add("open");
    });

    item.append(label, del);
    return item;
  }

  function renderDomains() {
    domainList.innerHTML = "";
    (data.domains[activeId] || []).forEach((d) => {
      domainList.appendChild(buildDomainItem(d.id, d.domain));
    });
  }

  domainSaveBtn.addEventListener("click", async () => {
    const domain = domainInput.value.trim();
    if (needSelection() || !domain) return;
    const ownerId = activeId;

    try {
      domainSaveBtn.disabled = true;
      const saved = await post("/api/manage/addBlockedDomain", { [idKey]: ownerId, domain });

      if (!data.domains[ownerId]) data.domains[ownerId] = [];
      data.domains[ownerId].push({ id: saved.id, domain: saved.domain });

      // only touch the screen if they're still looking at the same group/device
      if (activeId === ownerId) {
        domainList.appendChild(buildDomainItem(saved.id, saved.domain));
        domainInput.value = "";
      }
    } catch (error) {
      alert("Error adding domain: " + error.message);
    } finally {
      domainSaveBtn.disabled = false;
    }
  });

  domainInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") domainSaveBtn.click();
  });

  cancelDeleteBtn.addEventListener("click", () => {
    deletePopup.classList.remove("open");
    pendingDelete = null;
  });

  confirmDeleteBtn.addEventListener("click", async () => {
    if (!pendingDelete) return;
    const { id, item, ownerId } = pendingDelete;

    try {
      confirmDeleteBtn.disabled = true;
      await post("/api/manage/deleteBlockedDomain", { id });

      item.remove();
      const list = data.domains[ownerId];
      if (list) {
        const idx = list.findIndex((d) => d.id === id);
        if (idx !== -1) list.splice(idx, 1);
      }
      deletePopup.classList.remove("open");
      pendingDelete = null;
    } catch (error) {
      alert("Error removing domain: " + error.message);
    } finally {
      confirmDeleteBtn.disabled = false;
    }
  });

  safeModeToggle.addEventListener("change", async () => {
    const enabled = safeModeToggle.checked;
    if (needSelection()) {
      safeModeToggle.checked = !enabled;
      return;
    }
    const ownerId = activeId;

    try {
      safeModeToggle.disabled = true;
      await post("/api/manage/setSafeMode", { [idKey]: ownerId, enabled });
      data.safeMode[ownerId] = enabled;
    } catch (error) {
      if (activeId === ownerId) safeModeToggle.checked = !enabled;
      alert("Error updating safe mode: " + error.message);
    } finally {
      safeModeToggle.disabled = false;
    }
  });

  function select(id, name) {
    activeId = Number(id);
    nameBar.textContent = name;
    renderDomains();
    safeModeToggle.checked = !!data.safeMode[activeId];
  }

  function clear() {
    activeId = null;
    nameBar.textContent = emptyLabel;
    domainList.innerHTML = "";
    safeModeToggle.checked = false;
  }

  return { select, clear, post };
})();
