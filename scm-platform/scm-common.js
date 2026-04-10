// Общие функции для SCM-платформы (полная версия с поддержкой филиалов)

window.SCMData = (function() {
    // --- Работа с реестром аудитов ---
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

    // --- Работа с KPI (с привязкой к филиалу) ---
    function saveKPI(kpiId, data, branchId = null) {
        const bid = branchId || getCurrentBranch();
        localStorage.setItem(`kpi_${kpiId}_${bid}`, JSON.stringify({ ...data, timestamp: new Date().toISOString(), branchId: bid }));
    }

    function loadKPI(kpiId, branchId = null) {
        const bid = branchId || getCurrentBranch();
        const raw = localStorage.getItem(`kpi_${kpiId}_${bid}`);
        if (raw) return JSON.parse(raw);
        // fallback для миграции
        if (bid === 'default') {
            const oldRaw = localStorage.getItem(`kpi_${kpiId}`);
            return oldRaw ? JSON.parse(oldRaw) : null;
        }
        return null;
    }

    function getAllKPIs(branchId = null) {
        const bid = branchId || getCurrentBranch();
        const kpis = ['otd', 'fillrate', 'turnover', 'ccc', 'nps', 'pickErrors', 'productivity', 'spaceUtil', 'transportCost', 'deadhead', 'gmroi', 'stockout', 'scmCostPercent', 'ces', 'fcr', 'co2', 'wasteRate'];
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

    // --- Прогресс дорожной карты с привязкой к филиалу ---
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

    // --- Результаты аудита (последний) с привязкой к филиалу ---
    function saveAuditResult(result, branchId = null) {
        const bid = branchId || getCurrentBranch();
        localStorage.setItem(`last_audit_result_${bid}`, JSON.stringify(result));
    }

    function getLastAuditResult(branchId = null) {
        const bid = branchId || getCurrentBranch();
        const raw = localStorage.getItem(`last_audit_result_${bid}`);
        return raw ? JSON.parse(raw) : null;
    }

    // --- Экспорт всех данных (для отладки/бэкапа) ---
    function exportAllData(branchId = null) {
        const bid = branchId || getCurrentBranch();
        const keys = Object.keys(localStorage).filter(k => k.includes(bid) || (bid === 'default' && !k.includes('_default') && !k.includes('_history')));
        const data = {};
        keys.forEach(k => { data[k] = localStorage.getItem(k); });
        return JSON.stringify(data, null, 2);
    }

    function importAllData(jsonStr, branchId = null) {
        const bid = branchId || getCurrentBranch();
        try {
            const data = JSON.parse(jsonStr);
            for (const [key, value] of Object.entries(data)) {
                if (key.includes(bid) || (bid === 'default' && !key.includes('_'))) {
                    localStorage.setItem(key, value);
                }
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

// ==================== УПРАВЛЕНИЕ БИЗНЕС-ЕДИНИЦАМИ (ФИЛИАЛАМИ) ====================
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
        return filtered.map(b => ({
            ...b,
            children: buildTree(branches, b.id)
        }));
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
        getBranches,
        addBranch,
        updateBranch,
        deleteBranch,
        getBranchById,
        buildTree,
        ensureDefaultBranch,
        importBranches
    };
})();

// ==================== ГЛОБАЛЬНЫЙ КОНТЕКСТ ТЕКУЩЕЙ БИЗНЕС-ЕДИНИЦЫ ====================
let _currentBranchId = localStorage.getItem('scm_current_branch') || 'default';

function setCurrentBranch(branchId) {
    _currentBranchId = branchId;
    localStorage.setItem('scm_current_branch', branchId);
    window.dispatchEvent(new CustomEvent('branch-changed', { detail: { branchId } }));
}

function getCurrentBranch() {
    return _currentBranchId;
}

// ==================== МИГРАЦИЯ СТАРЫХ ДАННЫХ ====================
function migrateLegacyDataToDefaultBranch() {
    // KPI
    const kpiIds = ['otd', 'fillrate', 'turnover', 'ccc', 'nps', 'pickErrors', 'productivity', 'spaceUtil', 'transportCost', 'deadhead', 'gmroi', 'stockout', 'scmCostPercent', 'ces', 'fcr', 'co2', 'wasteRate'];
    for (let kpiId of kpiIds) {
        const oldData = localStorage.getItem(`kpi_${kpiId}`);
        if (oldData && !localStorage.getItem(`kpi_${kpiId}_default`)) {
            localStorage.setItem(`kpi_${kpiId}_default`, oldData);
        }
        const oldHistory = localStorage.getItem(`kpi_${kpiId}_history`);
        if (oldHistory && !localStorage.getItem(`kpi_${kpiId}_default_history`)) {
            localStorage.setItem(`kpi_${kpiId}_default_history`, oldHistory);
        }
    }
    // Аудиты
    const oldAuditRegistry = localStorage.getItem('audit_registry');
    if (oldAuditRegistry && !localStorage.getItem('audit_registry_default')) {
        let audits = JSON.parse(oldAuditRegistry);
        audits = audits.map(a => ({ ...a, branchId: 'default' }));
        localStorage.setItem('audit_registry_default', JSON.stringify(audits));
    }
    // Чек-листы
    const oldChecklists = localStorage.getItem('scm_checklists');
    if (oldChecklists && !localStorage.getItem('scm_checklists_default')) {
        localStorage.setItem('scm_checklists_default', oldChecklists);
    }
    // Дорожная карта
    const oldRoadmap = localStorage.getItem('roadmap_progress');
    if (oldRoadmap && !localStorage.getItem('roadmap_progress_default')) {
        localStorage.setItem('roadmap_progress_default', oldRoadmap);
    }
    // Задачи планера (scm_planner_tasks_v5) – переносим
    const oldTasks = localStorage.getItem('scm_planner_tasks_v5');
    if (oldTasks && !localStorage.getItem('scm_planner_tasks_v5_default')) {
        let tasks = JSON.parse(oldTasks);
        // Добавляем branchId к каждой задаче
        const newTasks = {};
        for (let [date, list] of Object.entries(tasks)) {
            newTasks[date] = list.map(t => ({ ...t, branchId: 'default' }));
        }
        localStorage.setItem('scm_planner_tasks_v5_default', JSON.stringify(newTasks));
    }
}
migrateLegacyDataToDefaultBranch();

// ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАДАЧАМИ ПЛАНЕРА (с филиалом) ====================
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

// ==================== ИНИЦИАЛИЗАЦИЯ НАВИГАЦИИ ====================
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = window.location.pathname.split('/').pop();
    const links = document.querySelectorAll('.sidebar nav a');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage) link.classList.add('active');
        else if (currentPage === '' && href === 'dashboard.html') link.classList.add('active');
    });

    // Бургер-меню для мобильных
    const toggleBtn = document.querySelector('.menu-toggle');
    if (toggleBtn) {
        const sidebar = document.querySelector('.sidebar');
        toggleBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
    }
});
