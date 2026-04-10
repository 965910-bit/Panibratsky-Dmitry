// ============================================================
// scm-common.js – ПОЛНАЯ ВЕРСИЯ С ПОДДЕРЖКОЙ ФИЛИАЛОВ, БЮДЖЕТА, ШТАТА
// ============================================================

// ---------- 1. ОБЩИЕ ДАННЫЕ SCM (KPI, АУДИТЫ, ЧЕК-ЛИСТЫ, ДОРОЖНАЯ КАРТА) ----------
window.SCMData = (function() {
    // --- Работа с реестром аудитов (с привязкой к филиалу) ---
    function getAuditRegistry(branchId = null) {
        const bid = branchId || getCurrentBranch();
        const reg = localStorage.getItem(`audit_registry_${bid}`);
        return reg ? JSON.parse(reg) : [];
    }
    function saveAuditRegistry(registry, branchId = null) {
        const bid = branchId || getCurrentBranch();
        localStorage.setItem(`audit_registry_${bid}`, JSON.stringify(registry));
    }
    function addAudit(auditData, branchId = null) {
        const bid = branchId || getCurrentBranch();
        const registry = getAuditRegistry(bid);
        auditData.id = Date.now().toString();
        auditData.createdAt = new Date().toISOString();
        auditData.branchId = bid;
        registry.push(auditData);
        saveAuditRegistry(registry, bid);
        return auditData.id;
    }
    function getAuditById(id, branchId = null) {
        const bid = branchId || getCurrentBranch();
        const registry = getAuditRegistry(bid);
        return registry.find(a => a.id === id);
    }
    function updateAudit(id, newData, branchId = null) {
        const bid = branchId || getCurrentBranch();
        let registry = getAuditRegistry(bid);
        const index = registry.findIndex(a => a.id === id);
        if (index !== -1) {
            registry[index] = { ...registry[index], ...newData, updatedAt: new Date().toISOString() };
            saveAuditRegistry(registry, bid);
        }
    }
    function deleteAudit(id, branchId = null) {
        const bid = branchId || getCurrentBranch();
        let registry = getAuditRegistry(bid);
        registry = registry.filter(a => a.id !== id);
        saveAuditRegistry(registry, bid);
    }

    // --- KPI с привязкой к филиалу ---
    function saveKPI(kpiId, data, branchId = null) {
        const bid = branchId || getCurrentBranch();
        localStorage.setItem(`kpi_${kpiId}_${bid}`, JSON.stringify({ ...data, timestamp: new Date().toISOString(), branchId: bid }));
    }
    function loadKPI(kpiId, branchId = null) {
        const bid = branchId || getCurrentBranch();
        const raw = localStorage.getItem(`kpi_${kpiId}_${bid}`);
        if (raw) return JSON.parse(raw);
        if (bid === 'default') {
            const oldRaw = localStorage.getItem(`kpi_${kpiId}`);
            return oldRaw ? JSON.parse(oldRaw) : null;
        }
        return null;
    }
    function getAllKPIs(branchId = null) {
        const bid = branchId || getCurrentBranch();
        const kpis = ['otd','fillrate','turnover','ccc','nps','pickErrors','productivity','spaceUtil','transportCost','deadhead','gmroi','stockout','scmCostPercent','ces','fcr','co2','wasteRate'];
        const result = {};
        kpis.forEach(k => { result[k] = loadKPI(k, bid); });
        return result;
    }
    function getKPIHistory(kpiId, branchId = null) {
        const bid = branchId || getCurrentBranch();
        const raw = localStorage.getItem(`kpi_${kpiId}_${bid}_history`);
        if (raw) return JSON.parse(raw);
        if (bid === 'default') {
            const oldRaw = localStorage.getItem(`kpi_${kpiId}_history`);
            return oldRaw ? JSON.parse(oldRaw) : [];
        }
        return [];
    }
    function saveKPIHistory(kpiId, history, branchId = null) {
        const bid = branchId || getCurrentBranch();
        localStorage.setItem(`kpi_${kpiId}_${bid}_history`, JSON.stringify(history));
    }

    // --- Чек-листы с привязкой к филиалу ---
    function saveChecklist(category, itemsState, branchId = null) {
        const bid = branchId || getCurrentBranch();
        localStorage.setItem(`checklist_${category}_${bid}`, JSON.stringify(itemsState));
    }
    function loadChecklist(category, branchId = null) {
        const bid = branchId || getCurrentBranch();
        const raw = localStorage.getItem(`checklist_${category}_${bid}`);
        if (raw) return JSON.parse(raw);
        if (bid === 'default') {
            const oldRaw = localStorage.getItem(`checklist_${category}`);
            return oldRaw ? JSON.parse(oldRaw) : {};
        }
        return {};
    }

    // --- Дорожная карта (прогресс) с привязкой к филиалу ---
    function saveRoadmapProgress(phaseId, progress, branchId = null) {
        const bid = branchId || getCurrentBranch();
        const all = JSON.parse(localStorage.getItem(`roadmap_progress_${bid}`) || '{}');
        all[phaseId] = progress;
        localStorage.setItem(`roadmap_progress_${bid}`, JSON.stringify(all));
    }
    function loadRoadmapProgress(branchId = null) {
        const bid = branchId || getCurrentBranch();
        return JSON.parse(localStorage.getItem(`roadmap_progress_${bid}`) || '{}');
    }

    // --- Результаты аудита ---
    function saveAuditResult(result, branchId = null) {
        const bid = branchId || getCurrentBranch();
        localStorage.setItem(`last_audit_result_${bid}`, JSON.stringify(result));
    }
    function getLastAuditResult(branchId = null) {
        const bid = branchId || getCurrentBranch();
        const raw = localStorage.getItem(`last_audit_result_${bid}`);
        return raw ? JSON.parse(raw) : null;
    }

    // --- Экспорт/импорт всех данных филиала ---
    function exportAllData(branchId = null) {
        const bid = branchId || getCurrentBranch();
        const keys = Object.keys(localStorage).filter(k => k.includes(bid));
        const data = {};
        keys.forEach(k => { data[k] = localStorage.getItem(k); });
        return JSON.stringify(data, null, 2);
    }
    function importAllData(jsonStr, branchId = null) {
        const bid = branchId || getCurrentBranch();
        try {
            const data = JSON.parse(jsonStr);
            for (const [key, value] of Object.entries(data)) {
                if (key.includes(bid)) localStorage.setItem(key, value);
            }
            return true;
        } catch(e) { return false; }
    }

    return {
        getAuditRegistry, saveAuditRegistry, addAudit, getAuditById, updateAudit, deleteAudit,
        saveKPI, loadKPI, getAllKPIs, getKPIHistory, saveKPIHistory,
        saveChecklist, loadChecklist,
        saveRoadmapProgress, loadRoadmapProgress,
        saveAuditResult, getLastAuditResult,
        exportAllData, importAllData
    };
})();

// ---------- 2. УПРАВЛЕНИЕ БИЗНЕС-ЕДИНИЦАМИ (ФИЛИАЛАМИ) ----------
window.BranchManager = (function() {
    const STORAGE_KEY = 'scm_branches';

    function getBranches() {
        const branches = localStorage.getItem(STORAGE_KEY);
        return branches ? JSON.parse(branches) : [];
    }
    function saveBranches(branches) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(branches));
        window.dispatchEvent(new CustomEvent('branches-updated'));
    }
    function addBranch(branch) {
        const branches = getBranches();
        const newId = Date.now().toString() + '_' + Math.random().toString(36).substr(2, 6);
        const newBranch = {
            id: newId,
            name: branch.name,
            type: branch.type || 'РЦ',
            parentId: branch.parentId || null,
            order: branch.order || 0,
            isActive: true,
            createdAt: new Date().toISOString(),
            metadata: branch.metadata || {}
        };
        branches.push(newBranch);
        saveBranches(branches);
        return newId;
    }
    function updateBranch(id, updates) {
        let branches = getBranches();
        const index = branches.findIndex(b => b.id === id);
        if (index !== -1) {
            branches[index] = { ...branches[index], ...updates, updatedAt: new Date().toISOString() };
            saveBranches(branches);
        }
    }
    function deleteBranch(id) {
        let branches = getBranches();
        const toDelete = new Set();
        const findChildren = (parentId) => {
            branches.forEach(b => {
                if (b.parentId === parentId && !toDelete.has(b.id)) {
                    toDelete.add(b.id);
                    findChildren(b.id);
                }
            });
        };
        toDelete.add(id);
        findChildren(id);
        branches = branches.filter(b => !toDelete.has(b.id));
        saveBranches(branches);
    }
    function getBranchById(id) {
        const branches = getBranches();
        return branches.find(b => b.id === id);
    }
    function buildTree(branches, parentId = null) {
        const filtered = branches.filter(b => b.parentId === parentId);
        return filtered.map(b => ({ ...b, children: buildTree(branches, b.id) }));
    }
    function ensureDefaultBranch() {
        let branches = getBranches();
        if (branches.length === 0) {
            const defaultBranch = {
                id: 'default',
                name: 'Головной офис',
                type: 'РЦ',
                parentId: null,
                order: 0,
                isActive: true,
                createdAt: new Date().toISOString(),
                metadata: {}
            };
            branches.push(defaultBranch);
            saveBranches(branches);
        }
        return branches;
    }
    function importBranches(branches) {
        saveBranches(branches);
    }
    return {
        getBranches, addBranch, updateBranch, deleteBranch, getBranchById, buildTree, ensureDefaultBranch, importBranches
    };
})();

// ---------- 3. ГЛОБАЛЬНЫЙ КОНТЕКСТ ТЕКУЩЕЙ БИЗНЕС-ЕДИНИЦЫ ----------
let _currentBranchId = localStorage.getItem('scm_current_branch') || 'default';
function setCurrentBranch(branchId) {
    _currentBranchId = branchId;
    localStorage.setItem('scm_current_branch', branchId);
    window.dispatchEvent(new CustomEvent('branch-changed', { detail: { branchId } }));
}
function getCurrentBranch() {
    return _currentBranchId;
}

// ---------- 4. БЮДЖЕТ ФИЛИАЛА ----------
function getBranchBudget(branchId, year) {
    const key = `branch_budget_${branchId}_${year}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : {};
}
function saveBranchBudget(branchId, year, budgetData) {
    const key = `branch_budget_${branchId}_${year}`;
    localStorage.setItem(key, JSON.stringify(budgetData));
}
function getBudgetMonths(branchId, year) {
    const budget = getBranchBudget(branchId, year);
    const months = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
    return months.map(month => ({
        month,
        opex: budget[month]?.opex || 0,
        payroll: budget[month]?.payroll || 0,
        transport: budget[month]?.transport || 0,
        capex: budget[month]?.capex || 0
    }));
}
function saveBudgetMonth(branchId, year, month, values) {
    const budget = getBranchBudget(branchId, year);
    budget[month] = { ...budget[month], ...values };
    saveBranchBudget(branchId, year, budget);
}

// ---------- 5. ШТАТНОЕ РАСПИСАНИЕ ФИЛИАЛА ----------
function getBranchStaff(branchId) {
    const key = `branch_staff_${branchId}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : [];
}
function saveBranchStaff(branchId, staffData) {
    const key = `branch_staff_${branchId}`;
    localStorage.setItem(key, JSON.stringify(staffData));
}
function addStaffPosition(branchId, position) {
    const staff = getBranchStaff(branchId);
    staff.push({ id: Date.now().toString(), ...position });
    saveBranchStaff(branchId, staff);
}
function updateStaffPosition(branchId, positionId, updates) {
    const staff = getBranchStaff(branchId);
    const index = staff.findIndex(p => p.id === positionId);
    if (index !== -1) {
        staff[index] = { ...staff[index], ...updates };
        saveBranchStaff(branchId, staff);
    }
}
function deleteStaffPosition(branchId, positionId) {
    let staff = getBranchStaff(branchId);
    staff = staff.filter(p => p.id !== positionId);
    saveBranchStaff(branchId, staff);
}

// ---------- 6. ЦЕЛЕВЫЕ KPI ФИЛИАЛА ----------
function getBranchKPITargets(branchId, year) {
    const key = `branch_kpi_targets_${branchId}_${year}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : {};
}
function saveBranchKPITargets(branchId, year, targets) {
    const key = `branch_kpi_targets_${branchId}_${year}`;
    localStorage.setItem(key, JSON.stringify(targets));
}
function setBranchKPITarget(branchId, year, kpiId, value) {
    const targets = getBranchKPITargets(branchId, year);
    targets[kpiId] = value;
    saveBranchKPITargets(branchId, year, targets);
}

// ---------- 7. ЗАДАЧИ ПЛАНЕРА С ПРИВЯЗКОЙ К ФИЛИАЛУ ----------
function getPlannerTasks(branchId = null) {
    const bid = branchId || getCurrentBranch();
    const raw = localStorage.getItem(`scm_planner_tasks_v5_${bid}`);
    if (raw) return JSON.parse(raw);
    if (bid === 'default') {
        const oldRaw = localStorage.getItem('scm_planner_tasks_v5');
        return oldRaw ? JSON.parse(oldRaw) : { backlog: [] };
    }
    return { backlog: [] };
}
function savePlannerTasks(tasks, branchId = null) {
    const bid = branchId || getCurrentBranch();
    localStorage.setItem(`scm_planner_tasks_v5_${bid}`, JSON.stringify(tasks));
}

// ---------- 8. МИГРАЦИЯ СТАРЫХ ДАННЫХ ----------
function migrateLegacyDataToDefaultBranch() {
    const kpiIds = ['otd','fillrate','turnover','ccc','nps','pickErrors','productivity','spaceUtil','transportCost','deadhead','gmroi','stockout','scmCostPercent','ces','fcr','co2','wasteRate'];
    for (let kpiId of kpiIds) {
        const oldData = localStorage.getItem(`kpi_${kpiId}`);
        if (oldData && !localStorage.getItem(`kpi_${kpiId}_default`)) localStorage.setItem(`kpi_${kpiId}_default`, oldData);
        const oldHistory = localStorage.getItem(`kpi_${kpiId}_history`);
        if (oldHistory && !localStorage.getItem(`kpi_${kpiId}_default_history`)) localStorage.setItem(`kpi_${kpiId}_default_history`, oldHistory);
    }
    const oldAudit = localStorage.getItem('audit_registry');
    if (oldAudit && !localStorage.getItem('audit_registry_default')) {
        let audits = JSON.parse(oldAudit);
        audits = audits.map(a => ({ ...a, branchId: 'default' }));
        localStorage.setItem('audit_registry_default', JSON.stringify(audits));
    }
    const oldChecklists = localStorage.getItem('scm_checklists');
    if (oldChecklists && !localStorage.getItem('scm_checklists_default')) localStorage.setItem('scm_checklists_default', oldChecklists);
    const oldRoadmap = localStorage.getItem('roadmap_progress');
    if (oldRoadmap && !localStorage.getItem('roadmap_progress_default')) localStorage.setItem('roadmap_progress_default', oldRoadmap);
    const oldTasks = localStorage.getItem('scm_planner_tasks_v5');
    if (oldTasks && !localStorage.getItem('scm_planner_tasks_v5_default')) {
        let tasks = JSON.parse(oldTasks);
        const newTasks = {};
        for (let [date, list] of Object.entries(tasks)) newTasks[date] = list.map(t => ({ ...t, branchId: 'default' }));
        localStorage.setItem('scm_planner_tasks_v5_default', JSON.stringify(newTasks));
    }
}
migrateLegacyDataToDefaultBranch();

// ---------- 9. НАВИГАЦИЯ (активный пункт меню) ----------
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = window.location.pathname.split('/').pop();
    const links = document.querySelectorAll('.sidebar nav a');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage) link.classList.add('active');
        else if (currentPage === '' && href === 'dashboard.html') link.classList.add('active');
    });
    const toggleBtn = document.querySelector('.menu-toggle');
    if (toggleBtn) {
        const sidebar = document.querySelector('.sidebar');
        toggleBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
    }
});
