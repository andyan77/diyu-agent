"use strict";

function completeSeriesOutline(outline) {
  return Array.isArray(outline)
    && outline.length === 3
    && outline.every((episode) => String(episode?.title || "").trim());
}

function createSeriesOutlineGate(loadOutline) {
  let pendingRequest = null;

  return {
    ensure(currentOutline) {
      if (completeSeriesOutline(currentOutline)) return Promise.resolve(currentOutline);
      if (pendingRequest) return pendingRequest;

      const request = Promise.resolve()
        .then(loadOutline)
        .then((outline) => {
          if (!completeSeriesOutline(outline)) {
            throw new Error("三集提纲暂时没有完成，请重试，或切回单篇。");
          }
          return outline;
        });
      pendingRequest = request;
      void request.then(
        () => { if (pendingRequest === request) pendingRequest = null; },
        () => { if (pendingRequest === request) pendingRequest = null; }
      );
      return request;
    },
    reset() {
      pendingRequest = null;
    }
  };
}

function formatSeriesOutline(outline) {
  return `三集提纲：${outline.map((episode) => {
    const description = String(episode.description || "").trim();
    return `${episode.index}.${episode.title}${description ? `（${description}）` : ""}`;
  }).join("；")}`;
}

function serializeSeriesOutline(outline) {
  return Array.isArray(outline) ? outline.map((episode, index) => ({
    episode_index: Number(episode.episode_index || episode.index || index + 1),
    title: String(episode.title || "").trim(),
    summary: String(episode.summary || episode.description || "").trim()
  })) : [];
}

function buildPortalTaskPayload(input) {
  return {
    account_display_name: String(input.accountDisplayName || ""),
    operation: input.operation,
    topic_label: input.topicLabel || null,
    primary_audience: input.primaryAudience || null,
    message: String(input.message || "").trim() || "请先帮我理一理现在最值得讲的内容。",
    target_platform: input.targetPlatform || "其他",
    candidate_number: input.candidateNumber ?? null,
    content_goal: input.contentGoal || null,
    key_takeaway: input.keyTakeaway || null,
    speaker_role_name: input.speakerRoleName || null,
    storyline_name: null,
    column_name: null,
    continue_previous: Boolean(input.continuePrevious),
    previous_content_ref: input.previousContentRef || null,
    localization_allowed: false,
    duration_label: input.durationLabel || "由系统建议",
    expression_feeling: input.expressionFeeling || "由系统建议",
    content_format: input.contentFormat || "短视频",
    organization_level: input.organizationLevel || null,
    content_identity: null,
    long_term_storyline: null,
    content_direction: null,
    business_goal: input.businessGoal || null,
    expression_method: null,
    existing_material_kinds: Array.isArray(input.existingMaterialKinds) ? input.existingMaterialKinds : [],
    series_mode: input.seriesMode || "SINGLE",
    episode_index: Number(input.episodeIndex || 1),
    series_outline: serializeSeriesOutline(input.seriesOutline)
  };
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function resetEpisodeOutputState(target, episodeIndex = 1) {
  target.episodeIndex = episodeIndex;
  target.candidates = [];
  target.legacyAnswer = "";
  target.selectedOrdinal = 1;
  target.selectionConfirmed = false;
  target.confirmedOrdinal = 0;
  target.versions = [];
  target.versionIndex = -1;
  target.revisionMessages = [];
  return target;
}

function clearTaskOutputState(target) {
  resetEpisodeOutputState(target, 1);
  target.seriesOutline = [];
  target.seriesNote = "";
  target.episodeWorkspaces = {};
  target.latestEpisodeIndex = 1;
  target.resolvedClassification = null;
  target.currentStage = "confirm";
  target.legalNextActions = [];
  target.creationEpoch = Number(target.creationEpoch || 0) + 1;
  target.maxStep = Math.min(Number(target.maxStep || 0), 2);
  return target;
}

function snapshotEpisodeOutput(target) {
  return cloneJson({
    contentFormat: target.contentFormat,
    episodeIndex: target.episodeIndex,
    candidates: target.candidates,
    legacyAnswer: target.legacyAnswer,
    selectedOrdinal: target.selectedOrdinal,
    selectionConfirmed: target.selectionConfirmed,
    confirmedOrdinal: target.confirmedOrdinal,
    versions: target.versions,
    versionIndex: target.versionIndex,
    revisionMessages: target.revisionMessages
  });
}

function restoreEpisodeOutput(target, snapshot) {
  const restored = cloneJson(snapshot);
  Object.assign(target, restored);
  return target;
}

async function runGenerationAfterOutline({
  seriesMode,
  currentOutline,
  ensureOutline,
  buildPayload,
  sendGeneration
}) {
  const outline = seriesMode === "SERIES"
    ? await ensureOutline(currentOutline)
    : currentOutline;
  const value = await sendGeneration(buildPayload(outline));
  return {outline, value};
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    buildPortalTaskPayload,
    clearTaskOutputState,
    createSeriesOutlineGate,
    formatSeriesOutline,
    resetEpisodeOutputState,
    restoreEpisodeOutput,
    runGenerationAfterOutline,
    serializeSeriesOutline,
    snapshotEpisodeOutput
  };
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
const portalBase = window.location.pathname.startsWith("/apps") ? "/apps" : "";
const endpoint = (path) => `${portalBase}${path}`;
const FORMATS = [
  "短视频",
  "图文",
  "直播内容包",
  "私域沟通内容",
  "门店线下物料",
  "培训与门店话术",
  "陈列搭配"
];
const STEP_ORDER = ["home", "angles", "confirm", "result"];
const DIRECTION_PRESETS = {
  "总部品牌账号": [
    ["讲讲品牌为什么存在", "从一次坚持、改变或真实选择开始。", "品牌和企业故事"],
    ["看衣服如何服务真实生活", "把商品放回孩子和家庭的一天。", "穿搭、试穿和选购建议"],
    ["说清商品为什么这样设计", "从一个细节、取舍或改版进入。", "商品为什么这样设计"],
    ["记录一群人如何把品牌做好", "讲团队、商品和门店背后的日常。", "团队幕后、跨岗位协作和岗位成长"]
  ],
  "创始人账号": [
    ["说说我今天的想法", "一句正在形成的判断也可以开始。", "创始人或主理人的工作日常与观点"],
    ["讲一段创业经历", "从一个真实节点讲变化。", "品牌和企业故事"],
    ["讲一次重要选择", "说清当时面对什么、为什么这样选。", "创始人或主理人的工作日常与观点"],
    ["记录我的工作日常", "跟着今天的一个片段往下讲。", "真实工作与人物"]
  ],
  "总部专业人设账号": [
    ["记录我的岗位日常", "跟着一项具体工作往下讲。", "真实工作与人物"],
    ["讲一个专业判断", "把问题、条件和判断过程说清楚。", "手艺、工艺与专业知识"],
    ["记录一次产品改变", "讲旧版哪里不顺、后来怎么改。", "产品研发与验证"],
    ["带大家看一次工作过程", "让动作、工具和协作自然进入内容。", "团队幕后、跨岗位协作和岗位成长"]
  ],
  "省级代理商账号": [
    ["讲本地顾客关心的事", "从当地天气、习惯和真实问题开始。", "城市、区域与本地生活"],
    ["讲区域门店故事", "把一家店或几家店的差异讲出来。", "城市门店与本地生活"],
    ["记录培训或服务", "让团队如何解决问题成为内容。", "门店日常与顾客服务"],
    ["复盘一段区域经营", "说清选择、代价和下一步。", "活动、直播、咨询、到店、私域和复购承接"]
  ],
  "总部直营门店账号": [
    ["记录新品到店", "从拆箱、整理和上架选一个片段。", "门店日常与顾客服务"],
    ["回答顾客问题", "把一线经常遇到的问题讲清楚。", "穿搭、试穿和选购建议"],
    ["记录陈列变化", "让调整前后的差异成为内容。", "陈列调整与空间经营"],
    ["讲店员工作日常", "跟着一个岗位完成一件事。", "真实工作与人物"]
  ],
  "加盟门店账号": [
    ["讲店里今天发生的事", "一件小事也可以，不必先想意义。", "门店日常与顾客服务"],
    ["讲一件商品或搭配", "从最熟悉的一件衣服开始。", "穿搭、试穿和选购建议"],
    ["回答顾客常问的问题", "把今天被问到的一句话告诉系统。", "用户问题与理性选择"],
    ["记录到店或陈列变化", "拍正在发生的动作，不需要大改造。", "陈列调整与空间经营"],
    ["讲店主或员工日常", "跟着一个人完成一件事。", "真实工作与人物"]
  ]
};

const ui = {
  loginSection: document.querySelector("#login-section"),
  loginForm: document.querySelector("#login-form"),
  loginFeedback: document.querySelector("#login-feedback"),
  workspace: document.querySelector("#workspace"),
  creativeWorkspace: document.querySelector("#creative-workspace"),
  adminWorkspace: document.querySelector("#admin-workspace"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionUser: document.querySelector("#session-user"),
  globalStatus: document.querySelector("#global-status"),
  toast: document.querySelector("#toast"),
  idea: document.querySelector("#idea-input"),
  homeResponse: document.querySelector("#home-response"),
  directions: document.querySelector("#direction-list"),
  angles: document.querySelector("#angle-list"),
  anglesMessage: document.querySelector("#angles-message"),
  heardText: document.querySelector("#heard-text"),
  angleDetail: document.querySelector("#angle-detail"),
  candidates: document.querySelector("#candidate-list"),
  artifact: document.querySelector("#artifact-content"),
  revisionInput: document.querySelector("#revision-input"),
  revisionThread: document.querySelector("#revision-thread")
};

const state = {
  options: {},
  principal: {},
  accounts: [],
  currentAccount: null,
  isAdmin: false,
  step: "home",
  maxStep: 0,
  startMode: "inspire",
  idea: "",
  selectedDirection: null,
  angles: [],
  selectedAngle: 0,
  angleMessage: "",
  detail: "",
  contentFormats: [...FORMATS],
  contentFormat: "短视频",
  platform: "其他",
  duration: "由系统建议",
  primaryAudience: "",
  expressionFeeling: "由系统建议",
  materialKinds: [],
  businessGoal: null,
  speakerRoleName: null,
  exampleDirection: null,
  resolvedClassification: null,
  currentStage: "home",
  legalNextActions: [],
  seriesMode: "SINGLE",
  seriesOutline: [],
  seriesNote: "",
  episodeIndex: 1,
  episodeWorkspaces: {},
  latestEpisodeIndex: 1,
  creationEpoch: 0,
  candidates: [],
  legacyAnswer: "",
  selectedOrdinal: 1,
  selectionConfirmed: false,
  confirmedOrdinal: 0,
  versions: [],
  versionIndex: -1,
  revisionMessages: [],
  admin: {
    accounts: [],
    organizations: [],
    accountFamilies: [],
    personaTypes: [],
    personaTypesByFamily: {},
    organizationKindsByFamily: {},
    principals: [],
    enterpriseProfile: {},
    organizationPeople: [],
    usage: [],
    systemStatus: {},
    contentProducts: []
  },
  busy: false
};

function pick(source, keys, fallback = "") {
  if (!source || typeof source !== "object") return fallback;
  for (const key of keys) {
    const value = source[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return fallback;
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function createElement(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = String(text);
  return node;
}

function setHidden(node, hidden) {
  node?.classList.toggle("hidden", hidden);
}

function setStatus(message, kind = "info") {
  ui.globalStatus.textContent = message || "";
  ui.globalStatus.dataset.kind = kind;
  setHidden(ui.globalStatus, !message);
}

function showToast(message) {
  if (!message) return;
  ui.toast.textContent = message;
  setHidden(ui.toast, false);
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => setHidden(ui.toast, true), 2600);
}

function setBusy(busy, message = "") {
  state.busy = busy;
  document.querySelectorAll("button").forEach((button) => {
    if (button.id === "logout") return;
    if (busy) {
      button.dataset.disabledBeforeBusy = String(button.disabled);
      button.disabled = true;
    } else if (button.dataset.disabledBeforeBusy !== undefined) {
      button.disabled = button.dataset.disabledBeforeBusy === "true";
      delete button.dataset.disabledBeforeBusy;
    }
  });
  if (message) setStatus(message);
  if (!busy && !message && ui.globalStatus.dataset.kind === "info") setStatus("");
  updateProgress();
  if (!busy && state.step === "result") renderResult();
}

async function requestJson(path, init = {}, fallbackMessage = "系统暂时无法完成请求，请稍后重试。") {
  const headers = new Headers(init.headers || {});
  headers.set("X-Diyu-Portal", "same-origin-v1");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(endpoint(path), {...init, headers, credentials: "same-origin"});
  const text = await response.text();
  let value = {};
  if (text) {
    try { value = JSON.parse(text); } catch { value = {user_visible_text: text}; }
  }
  if (!response.ok) {
    const message = pick(value, ["user_visible_text", "message", "error"], fallbackMessage);
    const errorType = String(pick(value, ["error_type"], response.status === 401 ? "SESSION_EXPIRED" : "SYSTEM_TEMPORARY"));
    if (path !== "/login" && errorType === "SESSION_EXPIRED") {
      enterLoginState("登录已失效，请重新登录。");
    }
    const error = new Error(String(message));
    error.status = response.status;
    error.errorType = errorType;
    error.response = value;
    throw error;
  }
  return value;
}

function normalizeDirection(item) {
  if (typeof item === "string") {
    return {label: item, description: "从这个方向开始讲。", prompt: item, topicLabel: item};
  }
  if (Array.isArray(item)) {
    return {
      label: String(item[0] || "从这个方向开始"),
      description: String(item[1] || ""),
      prompt: String(item[3] || item[0] || ""),
      topicLabel: String(item[2] || "") || null
    };
  }
  return {
    label: String(pick(item, ["label", "title", "display_name", "name"], "从这个方向开始")),
    description: String(pick(item, ["description", "summary", "hint"], "")),
    prompt: String(pick(item, ["prompt", "example", "seed", "message", "label", "title"], "")),
    topicLabel: pick(item, ["topic_label", "topic"], null)
  };
}

function normalizeAccount(item, root) {
  const value = typeof item === "string" ? {display_name: item} : (item || {});
  const displayName = String(pick(value, ["outward_account_name", "public_account_name", "display_name", "name"], "未命名账号"));
  const roles = root.roles_by_account || {};
  const roleFallback = asArray(roles[displayName])[0] || "";
  return {
    id: String(pick(value, ["account_id", "id", "account_ref"], displayName)),
    requestName: String(pick(value, ["display_name", "name"], displayName)),
    displayName,
    family: String(pick(value, ["account_family_display_name", "account_family", "family"], "")),
    persona: String(pick(value, ["persona_type_display_name", "persona_type", "persona"], roleFallback)),
    organization: String(pick(value, ["organization_display_name", "organization_name", "organization"], "")),
    organizationLevel: pick(value, ["organization_level"], null),
    employeeRole: String(pick(value, ["employee_role", "business_role", "role_display_name"], "")),
    speakerRole: String(pick(value, ["speaker_role_name"], roleFallback)),
    headline: String(pick(value, ["homepage_headline", "headline"], "")),
    intro: String(pick(value, ["homepage_intro", "intro"], "")),
    placeholder: String(pick(value, ["input_placeholder", "placeholder"], "")),
    recommendedFormat: String(pick(value, ["recommended_content_format", "recommended_format"], "")),
    recommendedPlatform: String(pick(value, ["recommended_platform", "target_platform"], "")),
    recommendedDuration: String(pick(value, ["recommended_duration", "duration_label"], "")),
    primaryAudience: String(pick(value, ["primary_audience"], "希望从这个账号获得真实、有用内容的人")),
    directions: asArray(pick(value, ["homepage_directions", "directions", "recommendations"], [])).map(normalizeDirection),
    raw: value
  };
}

function normalizePrincipal(root) {
  const value = root.principal || root.identity || root.current_principal || root.login_principal || {};
  return {
    id: String(pick(value, ["principal_id", "id"], "")),
    displayName: String(pick(value, ["display_name", "name", "login_user_name", "username"], "当前使用人")),
    employeeRole: String(pick(value, ["employee_role", "business_role", "role_display_name"], "")),
    organization: String(pick(value, ["organization_display_name", "organization_name", "organization"], "")),
    workspaceKind: String(pick(value, ["workspace_kind", "workspace_type", "workspace"], pick(root, ["workspace_kind", "workspace_type"], ""))),
    accountFamily: String(pick(value, ["account_family"], "")),
    isAdmin: Boolean(pick(value, ["is_admin", "enterprise_admin"], false))
  };
}

function activateWorkspace(payload) {
  const root = payload.options || payload;
  state.options = root;
  state.principal = normalizePrincipal(root);
  const rawAccounts = pick(root, ["accounts", "allowed_accounts", "content_accounts"], []);
  state.accounts = asArray(rawAccounts).map((item) => normalizeAccount(item, root));
  const workspaceKind = state.principal.workspaceKind.toUpperCase();
  state.isAdmin = state.principal.isAdmin || workspaceKind.includes("ADMIN") || state.principal.accountFamily === "企业管理员" || root.admin_workspace === true;
  const requestedAccount = String(pick(root, ["current_account_id", "current_account_ref", "current_account_display_name"], ""));
  state.currentAccount = state.accounts.find((account) => account.id === requestedAccount || account.displayName === requestedAccount) || state.accounts[0] || null;
  const formats = asArray(root.content_formats).filter((value) => FORMATS.includes(value));
  state.contentFormats = formats.length === FORMATS.length ? formats : [...FORMATS];
  const platforms = asArray(root.platforms);
  const durations = asArray(root.durations);
  const feelings = asArray(root.feelings);
  fillSimpleSelect(document.querySelector("#platform-select"), platforms.length ? platforms : ["其他"]);
  fillSimpleSelect(document.querySelector("#duration-select"), durations.length ? durations : ["由系统建议"]);
  fillSimpleSelect(document.querySelector("#feeling-select"), feelings.length ? feelings : ["由系统建议"]);
  state.platform = state.currentAccount?.recommendedPlatform || platforms[0] || "其他";
  state.duration = state.currentAccount?.recommendedDuration || (durations.includes("由系统建议") ? "由系统建议" : durations[0]) || "由系统建议";
  state.contentFormat = state.currentAccount?.recommendedFormat || state.contentFormats[0] || "短视频";

  ui.sessionUser.textContent = state.principal.displayName;
  setHidden(ui.sessionSummary, false);
  setHidden(ui.loginSection, true);
  setHidden(ui.workspace, false);
  setHidden(ui.adminWorkspace, !state.isAdmin);
  setHidden(ui.creativeWorkspace, state.isAdmin);
  ui.workspace.classList.toggle("admin-mode", state.isAdmin);
  renderIdentity();
  if (state.isAdmin) {
    configureAdmin(root.management || root.admin || root.account_matrix || {});
    loadAdminAccounts();
  } else {
    configureContentProductSearch();
    resetCreation();
  }
}

function enterLoginState(message) {
  seriesOutlineGate.reset();
  clearTaskOutputState(state);
  state.step = "home";
  state.maxStep = 0;
  state.principal = {};
  state.accounts = [];
  state.currentAccount = null;
  state.isAdmin = false;
  ui.loginForm.reset();
  ui.loginFeedback.textContent = message;
  ui.sessionUser.textContent = "";
  setHidden(ui.sessionSummary, true);
  setHidden(ui.workspace, true);
  setHidden(ui.adminWorkspace, true);
  setHidden(ui.creativeWorkspace, true);
  setHidden(ui.loginSection, false);
}

function renderIdentity() {
  const account = state.currentAccount;
  const principal = state.principal;
  const family = state.isAdmin ? "企业管理员" : (account?.family || "内容创作账号");
  const persona = state.isAdmin ? "企业管理" : (account?.persona || account?.speakerRole || "当前账号人设");
  const outward = state.isAdmin ? "不参与内容创作" : (account?.displayName || "—");
  document.querySelector("#identity-title").textContent = state.isAdmin ? "企业管理工作区" : outward;
  document.querySelector("#identity-persona").textContent = state.isAdmin ? "管理企业资料、人员和账号矩阵" : persona;
  document.querySelector("#identity-principal").textContent = principal.displayName || "—";
  document.querySelector("#identity-role").textContent = principal.employeeRole || account?.employeeRole || "—";
  document.querySelector("#identity-organization").textContent = account?.organization || principal.organization || "—";
  document.querySelector("#identity-family").textContent = family;
  document.querySelector("#identity-persona-type").textContent = persona;
  document.querySelector("#identity-account").textContent = outward;
  document.querySelector("#identity-product").textContent = state.isAdmin
    ? "不参与内容创作"
    : (state.resolvedClassification?.content_product || "尚未分类");
  document.querySelector("#identity-format").textContent = state.isAdmin
    ? "不参与内容创作"
    : (state.contentFormat || "由系统建议");

  const wrap = document.querySelector("#account-switcher-wrap");
  const select = document.querySelector("#account-switcher");
  select.replaceChildren();
  state.accounts.forEach((row) => select.add(new Option(row.displayName, row.id)));
  if (account) select.value = account.id;
  setHidden(wrap, state.isAdmin || state.accounts.length < 2);
}

function accountDirections() {
  if (state.currentAccount?.directions.length >= 3) return state.currentAccount.directions.slice(0, 5);
  const preset = DIRECTION_PRESETS[state.currentAccount?.family];
  if (preset) return preset.map(normalizeDirection).slice(0, 5);
  return asArray(state.options.topics).slice(0, 5).map(normalizeDirection);
}

function resetCreation() {
  seriesOutlineGate.reset();
  clearTaskOutputState(state);
  state.step = "home";
  state.maxStep = 0;
  state.startMode = "inspire";
  state.idea = "";
  state.selectedDirection = null;
  state.angles = [];
  state.selectedAngle = 0;
  state.angleMessage = "";
  state.detail = "";
  state.seriesMode = "SINGLE";
  state.contentFormat = state.currentAccount?.recommendedFormat || state.contentFormats[0] || "短视频";
  state.platform = state.currentAccount?.recommendedPlatform || asArray(state.options.platforms)[0] || "其他";
  state.duration = state.currentAccount?.recommendedDuration || (asArray(state.options.durations).includes("由系统建议") ? "由系统建议" : asArray(state.options.durations)[0]) || "由系统建议";
  state.primaryAudience = state.currentAccount?.primaryAudience || "希望从这个账号获得真实、有用内容的人";
  state.expressionFeeling = "由系统建议";
  state.materialKinds = [];
  state.businessGoal = null;
  state.speakerRoleName = state.currentAccount?.speakerRole || null;
  state.exampleDirection = null;
  state.resolvedClassification = null;
  state.currentStage = "home";
  state.legalNextActions = [];
  ui.idea.value = "";
  ui.angleDetail.value = "";
  ui.revisionInput.value = "";
  document.querySelector("#content-product-search").value = "";
  setHidden(ui.homeResponse, true);
  configureQuickFill();
  document.querySelectorAll("[data-start-mode]").forEach((button) => button.classList.toggle("selected", button.dataset.startMode === state.startMode));
  document.querySelectorAll("[data-example-direction]").forEach((button) => button.classList.remove("selected"));
  renderHome();
  renderIdentity();
  setStep("home");
}

function hasTaskOutput() {
  return state.candidates.length > 0 || state.versions.length > 0 || Object.keys(state.episodeWorkspaces).length > 0;
}

function clearTaskOutputUi() {
  ui.revisionInput.value = "";
  ui.candidates.replaceChildren();
  ui.artifact.replaceChildren();
  ui.revisionThread.replaceChildren();
  document.querySelector("#version-label").textContent = "";
  document.querySelector("#result-episode").textContent = "";
  document.querySelector("#episode-history").replaceChildren();
}

function beginNewCreationTask(seriesMode) {
  seriesOutlineGate.reset();
  clearTaskOutputState(state);
  state.seriesMode = seriesMode;
  clearTaskOutputUi();
  setStep("confirm");
}

function saveCurrentEpisodeWorkspace() {
  if (state.seriesMode !== "SERIES" || !state.candidates.length) return;
  state.episodeWorkspaces[String(state.episodeIndex)] = snapshotEpisodeOutput(state);
}

function showEpisode(episodeIndex) {
  if (episodeIndex === state.episodeIndex) return;
  const workspace = state.episodeWorkspaces[String(episodeIndex)];
  if (!workspace) return;
  saveCurrentEpisodeWorkspace();
  restoreEpisodeOutput(state, workspace);
  ui.revisionInput.value = "";
  setStep("result");
}

function renderHome() {
  const account = state.currentAccount;
  document.querySelector("#creative-title").textContent = "今天我可以怎样帮你？";
  document.querySelector("#creative-intro").textContent = account?.intro || account?.headline || "一句话、一件事或一个模糊想法都可以。";
  ui.idea.placeholder = account?.placeholder || "比如：今天发生了一件小事，我不知道值不值得讲。";
  ui.directions.replaceChildren();
  accountDirections().forEach((direction, index) => {
    const button = createElement("button", "direction-card");
    button.type = "button";
    button.dataset.directionIndex = String(index);
    button.append(
      createElement("span", "direction-index", String(index + 1).padStart(2, "0")),
      createElement("strong", "", direction.label),
      createElement("p", "", direction.description)
    );
    ui.directions.append(button);
  });
}

function configureQuickFill() {
  const speaker = document.querySelector("#quick-speaker");
  speaker.replaceChildren(new Option("当前账号（系统建议）", ""));
  if (state.currentAccount?.speakerRole) {
    speaker.add(new Option(state.currentAccount.speakerRole, state.currentAccount.speakerRole));
  }
  speaker.value = state.speakerRoleName || "";
  document.querySelector("#quick-material").value = state.materialKinds[0] || "";
  document.querySelector("#quick-format").value = state.contentFormat;
  document.querySelector("#quick-goal").value = state.businessGoal || "";
}

function configureContentProductSearch() {
  const list = document.querySelector("#content-product-suggestions");
  list.replaceChildren();
  asArray(state.options.content_products).forEach((product) => {
    const displayName = String(pick(product, ["display_name"], ""));
    if (!displayName) return;
    const option = document.createElement("option");
    option.value = displayName;
    const aliases = asArray(product.search_aliases).join("、");
    if (aliases) option.label = aliases;
    list.append(option);
  });
}

function setStep(step) {
  const index = STEP_ORDER.indexOf(step);
  if (index < 0) return;
  state.step = step;
  state.maxStep = Math.max(state.maxStep, index);
  STEP_ORDER.forEach((name) => setHidden(document.querySelector(`#step-${name}`), name !== step));
  updateProgress();
  if (step === "angles") renderAngles();
  if (step === "confirm") renderConfirm();
  if (step === "result") renderResult();
  document.querySelector(`#step-${step}`)?.scrollIntoView({behavior: "smooth", block: "start"});
}

function updateProgress() {
  document.querySelectorAll("[data-step]").forEach((button) => {
    const index = STEP_ORDER.indexOf(button.dataset.step);
    button.classList.toggle("current", button.dataset.step === state.step);
    button.classList.toggle("done", index < STEP_ORDER.indexOf(state.step));
    button.disabled = state.busy || index > state.maxStep;
    if (button.dataset.step === state.step) button.setAttribute("aria-current", "step");
    else button.removeAttribute("aria-current");
  });
}

function selectedAngle() {
  return state.angles[state.selectedAngle] || null;
}

function validTopicLabel() {
  const topic = state.selectedDirection?.topicLabel || selectedAngle()?.topicLabel;
  const allowed = asArray(state.options.topics);
  if (topic && (!allowed.length || allowed.includes(topic))) return topic;
  return null;
}

function taskPayload(operation, overrides = {}) {
  const account = state.currentAccount;
  const angle = selectedAngle();
  const message = String(overrides.message ?? state.idea ?? "").trim();
  return buildPortalTaskPayload({
    accountDisplayName: account?.requestName || account?.displayName || "",
    operation,
    topicLabel: overrides.topic_label !== undefined ? overrides.topic_label : validTopicLabel(),
    primaryAudience: state.primaryAudience || account?.primaryAudience,
    message,
    targetPlatform: overrides.target_platform || state.platform,
    candidateNumber: overrides.candidate_number,
    contentGoal: angle?.label || state.exampleDirection,
    keyTakeaway: state.detail,
    speakerRoleName: state.speakerRoleName || account?.speakerRole,
    continuePrevious: overrides.continue_previous,
    previousContentRef: overrides.previous_content_ref,
    durationLabel: state.duration,
    expressionFeeling: state.expressionFeeling,
    contentFormat: overrides.content_format || state.contentFormat,
    organizationLevel: account?.organizationLevel,
    businessGoal: state.businessGoal,
    existingMaterialKinds: state.materialKinds.length
      ? state.materialKinds
      : (state.startMode === "improve" ? ["一段故事或概要"] : []),
    seriesMode: overrides.series_mode || state.seriesMode,
    episodeIndex: overrides.episode_index || state.episodeIndex,
    seriesOutline: overrides.series_outline || state.seriesOutline
  });
}

async function sendTask(operation, overrides = {}) {
  const value = await requestJson("/v1/portal/chat", {
    method: "POST",
    body: JSON.stringify(taskPayload(operation, overrides))
  });
  state.currentStage = String(pick(value, ["current_stage", "stage"], pick(value, ["ui_state"], state.currentStage)));
  state.legalNextActions = asArray(pick(value, ["legal_next_actions", "allowed_actions"], []));
  const resolved = pick(value, ["resolved_classification"], null);
  if (resolved && typeof resolved === "object") {
    state.resolvedClassification = resolved;
    renderIdentity();
  }
  if (value.error_type) {
    const error = new Error(responseAnswer(value));
    error.errorType = String(value.error_type);
    error.response = value;
    throw error;
  }
  return value;
}

function responseAnswer(value) {
  return String(pick(value, ["answer", "user_visible_text", "message"], pick(value.ui_state, ["answer", "message"], "")));
}

function normalizeAngle(item, index) {
  if (typeof item === "string") return {label: item, description: "", topicLabel: null, index};
  return {
    label: String(pick(item, ["label", "title", "angle", "name"], `方向 ${index + 1}`)),
    description: String(pick(item, ["description", "summary", "reason", "why"], "")),
    topicLabel: pick(item, ["topic_label", "topic"], null),
    index
  };
}

function extractAngles(value) {
  const uiState = value.ui_state || {};
  const raw = pick(value, ["angles", "direction_options"], pick(uiState, ["angles", "direction_options"], []));
  return asArray(raw).slice(0, 3).map(normalizeAngle);
}

function normalizeEpisode(item, index) {
  if (typeof item === "string") return {index: index + 1, title: item, description: ""};
  return {
    index: Number(pick(item, ["episode_index", "index", "ordinal"], index + 1)),
    title: String(pick(item, ["title", "label", "topic", "name"], `第 ${index + 1} 集`)),
    description: String(pick(item, ["description", "summary", "difference"], ""))
  };
}

function extractSeries(value) {
  const uiState = value.ui_state || {};
  const series = value.series || uiState.series || {};
  const raw = Array.isArray(series) ? series : pick(series, ["outline", "episodes", "items"], []);
  return asArray(raw).slice(0, 3).map(normalizeEpisode);
}

async function requestSeriesOutline() {
  const value = await sendTask("找点灵感", {
    message: `${state.idea}\n请先规划三集彼此不同、但主题连续的通俗提纲。`,
    series_mode: "SERIES",
    episode_index: 1
  });
  return extractSeries(value);
}

const seriesOutlineGate = createSeriesOutlineGate(requestSeriesOutline);

function extractCandidates(value) {
  const uiState = value.ui_state || {};
  const result = value.result || {};
  return asArray(pick(value, ["candidates"], pick(uiState, ["candidates", "candidate_set"], pick(result, ["candidates"], []))));
}

async function requestAngles(mode, direction = null) {
  state.startMode = mode;
  state.idea = ui.idea.value.trim();
  if (direction) {
    state.selectedDirection = direction;
    state.idea = direction.prompt || direction.label;
    ui.idea.value = state.idea;
  }
  if (!state.idea && mode !== "inspire") {
    setStatus(mode === "improve" ? "请先贴入或概括想修改的旧内容。" : "请先用一句话说说想做什么。", "warning");
    ui.idea.focus();
    return;
  }
  const baseMessage = state.idea || "我还没有想好，请结合当前账号给我三个容易开始的内容方向。";
  const message = state.exampleDirection
    ? `${baseMessage}\n请围绕本次主题，从“${state.exampleDirection}”这个方向帮助我展开，不沿用任何示例原文或固定结构。`
    : baseMessage;
  try {
    setBusy(true, "正在理解你的想法…");
    const value = await sendTask("找点灵感", {message, topic_label: direction?.topicLabel || validTopicLabel()});
    state.angles = extractAngles(value);
    state.seriesOutline = extractSeries(value);
    state.angleMessage = state.angles.length ? "" : responseAnswer(value);
    if (!state.angles.length) {
      state.angles = [{
        label: direction?.label || "按当前想法继续",
        description: state.angleMessage || "保留原始主题，由系统继续完成。",
        topicLabel: direction?.topicLabel || validTopicLabel(),
        index: 0
      }];
    }
    state.selectedAngle = 0;
    setStep("angles");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function renderAngles() {
  ui.heardText.textContent = state.idea || "我还没有明确方向";
  ui.anglesMessage.textContent = state.angleMessage;
  setHidden(ui.anglesMessage, !state.angleMessage);
  ui.angles.replaceChildren();
  state.angles.forEach((angle, index) => {
    const button = createElement("button", `angle-card${index === state.selectedAngle ? " selected" : ""}`);
    button.type = "button";
    button.dataset.angleIndex = String(index);
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", String(index === state.selectedAngle));
    button.append(
      createElement("span", "angle-index", `方向 ${index + 1}`),
      createElement("strong", "", angle.label),
      createElement("p", "", angle.description)
    );
    ui.angles.append(button);
  });
}

function renderConfirm() {
  const angle = selectedAngle() || {label: "按当前想法继续", description: state.idea};
  document.querySelector("#confirm-theme").value = state.idea;
  document.querySelector("#confirm-angle-description").textContent = [
    state.exampleDirection ? `内容方向：${state.exampleDirection}` : "",
    angle.label,
    angle.description
  ].filter(Boolean).join("｜");
  document.querySelector("#confirmed-account").textContent = state.currentAccount?.displayName || "当前账号";
  document.querySelector("#confirmed-audience").textContent = state.primaryAudience || "由系统建议";
  document.querySelector("#recommended-format").textContent = state.contentFormat;
  document.querySelector("#recommended-platform").textContent = state.platform;
  document.querySelector("#recommended-duration").textContent = state.duration;
  document.querySelector("#recommended-persona").textContent = state.currentAccount?.persona || "当前账号人设";
  document.querySelector("#platform-select").value = state.platform;
  document.querySelector("#duration-select").value = state.duration;
  document.querySelector("#audience-input").value = state.primaryAudience;
  document.querySelector("#feeling-select").value = state.expressionFeeling;
  document.querySelectorAll("[data-series-mode]").forEach((button) => button.classList.toggle("selected", button.dataset.seriesMode === state.seriesMode));
  const formatOptions = document.querySelector("#format-options");
  formatOptions.replaceChildren();
  FORMATS.forEach((format) => {
    const button = createElement("button", format === state.contentFormat ? "choice selected" : "choice", format);
    button.type = "button";
    button.dataset.format = format;
    button.setAttribute("aria-pressed", String(format === state.contentFormat));
    formatOptions.append(button);
  });
  renderSeriesPlan();
}

function renderSeriesPlan() {
  const panel = document.querySelector("#series-plan");
  setHidden(panel, state.seriesMode !== "SERIES");
  const list = document.querySelector("#series-outline");
  list.replaceChildren();
  state.seriesOutline.forEach((episode) => {
    const item = createElement("li");
    item.append(createElement("strong", "", episode.title));
    if (episode.description) item.append(createElement("span", "", episode.description));
    list.append(item);
  });
  document.querySelector("#series-outline-note").textContent = state.seriesNote || (state.seriesOutline.length ? "先生成第1集，完成后再继续下一集。" : "正在等待系统给出三集差异化提纲。");
}

async function chooseSeriesMode(mode) {
  if (mode !== state.seriesMode) beginNewCreationTask(mode);
  state.seriesMode = mode;
  state.episodeIndex = 1;
  if (mode !== "SERIES") {
    state.seriesNote = "";
    renderConfirm();
    return;
  }
  if (completeSeriesOutline(state.seriesOutline)) {
    state.seriesNote = "先生成第1集，完成后再继续下一集。";
    renderConfirm();
    return;
  }
  const creationEpoch = state.creationEpoch;
  state.seriesNote = "正在规划三集提纲…";
  renderConfirm();
  try {
    const outline = await seriesOutlineGate.ensure(state.seriesOutline);
    if (state.seriesMode === "SERIES" && state.creationEpoch === creationEpoch) {
      state.seriesOutline = outline;
      state.seriesNote = "先生成第1集，完成后再继续下一集。";
    }
  } catch (_error) {
    if (state.seriesMode === "SERIES" && state.creationEpoch === creationEpoch) {
      state.seriesNote = "三集提纲暂时没有完成，请重试，或切回单篇。";
      setStatus(state.seriesNote, "error");
    }
  }
  if (state.seriesMode === "SERIES" && state.creationEpoch === creationEpoch) renderSeriesPlan();
}

function creationMessage(episodeIndex) {
  const angle = selectedAngle();
  const lines = [state.idea];
  if (angle?.label) lines.push(`切入角度：${angle.label}`);
  if (state.exampleDirection) lines.push(`用户选择的内容方向：${state.exampleDirection}`);
  if (state.detail) lines.push(`必须保留的细节：${state.detail}`);
  if (state.seriesMode === "SERIES") {
    if (state.seriesOutline.length) lines.push(formatSeriesOutline(state.seriesOutline));
    lines.push(`本次生成第${episodeIndex}集，保持连续但不要只换标题。`);
  }
  return lines.filter(Boolean).join("\n");
}

function pushVersion(candidates, legacyAnswer, selectionConfirmed = false) {
  const serverSelected = asArray(candidates).find((candidate) => candidate.selected === true);
  const initialOrdinal = serverSelected ? candidateOrdinal(serverSelected, asArray(candidates).indexOf(serverSelected)) : candidateOrdinal(candidates?.[0], 0);
  if (state.versionIndex < state.versions.length - 1) state.versions = state.versions.slice(0, state.versionIndex + 1);
  state.versions.push({
    candidates: JSON.parse(JSON.stringify(candidates || [])),
    legacyAnswer: legacyAnswer || "",
    contentFormat: state.contentFormat,
    episodeIndex: state.episodeIndex,
    selectedOrdinal: initialOrdinal,
    selectionConfirmed,
    confirmedOrdinal: selectionConfirmed ? initialOrdinal : 0
  });
  state.versionIndex = state.versions.length - 1;
  loadVersion(state.versionIndex);
}

function loadVersion(index) {
  const version = state.versions[index];
  if (!version) return;
  state.versionIndex = index;
  state.candidates = JSON.parse(JSON.stringify(version.candidates));
  state.legacyAnswer = version.legacyAnswer;
  state.contentFormat = version.contentFormat;
  state.episodeIndex = version.episodeIndex;
  state.selectedOrdinal = version.selectedOrdinal;
  state.selectionConfirmed = version.selectionConfirmed;
  state.confirmedOrdinal = version.confirmedOrdinal || 0;
  renderIdentity();
  if (state.step === "result") renderResult();
}

async function generateContent({nextEpisode = false} = {}) {
  if (!nextEpisode && hasTaskOutput()) beginNewCreationTask(state.seriesMode);
  const episode = nextEpisode ? Math.min(3, state.episodeIndex + 1) : 1;
  const operation = nextEpisode ? "继续一个系列" : "直接做内容";
  const previousContentRef = nextEpisode
    ? String(pick(selectedCandidateRecord(), ["continuation_ref"], ""))
    : "";
  if (nextEpisode && !previousContentRef) {
    setStatus("上一集上下文已失效，请返回当前系列上一集后重试。", "error");
    return;
  }
  try {
    const generationStatus = nextEpisode ? `正在生成第${episode}集…` : "正在生成第一版…";
    const waitingForOutline = state.seriesMode === "SERIES" && !completeSeriesOutline(state.seriesOutline);
    setBusy(true, waitingForOutline ? "正在等待三集提纲…" : generationStatus);
    const {value} = await runGenerationAfterOutline({
      seriesMode: state.seriesMode,
      currentOutline: state.seriesOutline,
      ensureOutline: (outline) => seriesOutlineGate.ensure(outline),
      buildPayload: (outline) => {
        if (state.seriesMode === "SERIES") {
          state.seriesOutline = outline;
          state.seriesNote = "先生成第1集，完成后再继续下一集。";
          renderSeriesPlan();
          setStatus(generationStatus);
        }
        return {
          message: creationMessage(episode),
          continue_previous: nextEpisode,
          previous_content_ref: previousContentRef || null,
          series_mode: state.seriesMode,
          episode_index: episode,
          content_format: state.contentFormat,
          series_outline: outline
        };
      },
      sendGeneration: (payload) => sendTask(operation, payload)
    });
    if (nextEpisode) {
      saveCurrentEpisodeWorkspace();
      resetEpisodeOutputState(state, episode);
      ui.revisionInput.value = "";
    }
    state.episodeIndex = episode;
    state.latestEpisodeIndex = Math.max(state.latestEpisodeIndex, episode);
    const outline = extractSeries(value);
    if (outline.length) state.seriesOutline = outline;
    const candidates = extractCandidates(value);
    const answer = responseAnswer(value);
    if (!candidates.length) throw new Error(answer || "本次没有生成可用成品，请调整想法后再试。");
    pushVersion(candidates, candidates.length ? "" : answer, candidates.some((candidate) => candidate.selected === true));
    state.revisionMessages.push({kind: "assistant", text: nextEpisode ? `第${episode}集已经生成。` : "第一版已经生成，可以直接选择并修改。"});
    setStep("result");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function candidateOrdinal(candidate, index) {
  return Number(pick(candidate, ["ordinal", "candidate_number", "index"], index + 1));
}

function candidatePayload(candidate) {
  const payload = candidate?.candidate_payload || candidate?.payload || candidate || {};
  const surfaces = payload.candidate_user_visible_surfaces || candidate?.candidate_user_visible_surfaces || candidate?.surfaces || payload;
  const execution = surfaces.execution_payload || candidate?.execution_payload || {};
  return {raw: candidate || {}, payload, surfaces, execution};
}

function candidateTitle(candidate, index) {
  const {surfaces} = candidatePayload(candidate);
  return String(pick(surfaces, ["title", "headline"], `方案 ${index + 1}`));
}

function candidateDifference(candidate) {
  const {raw, payload} = candidatePayload(candidate);
  return String(pick(raw, ["creative_difference", "difference_label", "difference"], pick(payload, ["creative_difference", "difference_label"], "")));
}

function renderResult() {
  document.querySelector("#result-product").textContent = state.resolvedClassification?.content_product || "系统已完成内容分类";
  document.querySelector("#result-format").textContent = state.contentFormat;
  document.querySelector("#result-episode").textContent = state.seriesMode === "SERIES" ? `3集系列 · 第${state.episodeIndex}集` : "单篇";
  document.querySelector("#version-label").textContent = `第 ${state.versionIndex + 1} 版`;
  document.querySelector("#previous-version").disabled = state.busy || state.versionIndex <= 0;
  renderEpisodeHistory();
  const historicalEpisode = state.seriesMode === "SERIES" && state.episodeIndex < state.latestEpisodeIndex;
  ui.revisionInput.disabled = historicalEpisode;
  document.querySelector("#apply-revision").disabled = state.busy || historicalEpisode;
  document.querySelector("#export-result").disabled = state.busy || historicalEpisode;
  const next = document.querySelector("#next-episode");
  setHidden(next, state.seriesMode !== "SERIES" || state.episodeIndex >= 3);
  if (state.seriesMode === "SERIES" && state.episodeIndex < 3) {
    const nextEpisodeSaved = Boolean(state.episodeWorkspaces[String(state.episodeIndex + 1)]);
    next.textContent = `${nextEpisodeSaved ? "查看" : "继续"}第${state.episodeIndex + 1}集`;
  }
  renderCandidateCards();
  renderArtifact();
  renderRevisionThread();
}

function renderEpisodeHistory() {
  const wrap = document.querySelector("#episode-history");
  wrap.replaceChildren();
  if (state.seriesMode !== "SERIES") return;
  const available = new Set(Object.keys(state.episodeWorkspaces).map(Number));
  if (state.candidates.length) available.add(state.episodeIndex);
  [...available].sort().forEach((episodeIndex) => {
    const button = createElement("button", episodeIndex === state.episodeIndex ? "selected" : "", `第${episodeIndex}集`);
    button.type = "button";
    button.dataset.episodeIndex = String(episodeIndex);
    button.disabled = episodeIndex === state.episodeIndex;
    wrap.append(button);
  });
}

function renderCandidateCards() {
  ui.candidates.replaceChildren();
  setHidden(ui.candidates, !state.candidates.length);
  state.candidates.forEach((candidate, index) => {
    const ordinal = candidateOrdinal(candidate, index);
    const selected = state.selectionConfirmed && ordinal === state.confirmedOrdinal;
    const button = createElement("button", `candidate-card${selected ? " selected" : ""}`);
    button.type = "button";
    button.dataset.candidateOrdinal = String(ordinal);
    button.disabled = state.seriesMode === "SERIES" && state.episodeIndex < state.latestEpisodeIndex;
    button.setAttribute("aria-pressed", String(selected));
    button.append(
      createElement("span", "candidate-label", state.candidates.length === 1 ? "当前方案" : `方案 ${index + 1}`),
      createElement("strong", "", candidateTitle(candidate, index))
    );
    const difference = candidateDifference(candidate);
    if (difference) button.append(createElement("small", "", difference));
    ui.candidates.append(button);
  });
}

function selectedCandidateRecord() {
  return state.candidates.find((candidate, index) => candidateOrdinal(candidate, index) === state.selectedOrdinal) || state.candidates[0] || null;
}

function appendTextSection(parent, title, value) {
  if (!value) return;
  const section = createElement("section", "result-block");
  section.append(createElement("h2", "", title), createElement("p", "result-copy", value));
  parent.append(section);
}

function appendListSection(parent, title, values) {
  const rows = asArray(values).filter((value) => value !== null && value !== undefined && value !== "");
  if (!rows.length) return;
  const section = createElement("section", "result-block");
  section.append(createElement("h2", "", title));
  const list = createElement("ul", "result-list");
  rows.forEach((row) => list.append(createElement("li", "", typeof row === "string" ? row : String(pick(row, ["text", "label", "title", "copy"], "")))));
  section.append(list);
  parent.append(section);
}

function formatDeliverable(record) {
  const {raw, payload, surfaces, execution} = record;
  const direct = raw.deliverable || payload.deliverable || surfaces.deliverable;
  if (direct && typeof direct === "object") return direct;
  const keys = {
    "短视频": ["short_video", "video"],
    "图文": ["article"],
    "直播内容包": ["live"],
    "私域沟通内容": ["private_communication", "private_messages"],
    "门店线下物料": ["offline_material"],
    "培训与门店话术": ["training"],
    "陈列搭配": ["display"]
  }[state.contentFormat] || [];
  for (const key of keys) if (execution[key] && typeof execution[key] === "object") return execution[key];
  return execution;
}

function renderArtifact() {
  ui.artifact.replaceChildren();
  const candidate = selectedCandidateRecord();
  if (!candidate) {
    if (state.legacyAnswer) ui.artifact.append(createElement("pre", "legacy-result", state.legacyAnswer));
    else ui.artifact.append(createElement("p", "empty-state", "当前响应没有可展示的成品。"));
    return;
  }
  const record = candidatePayload(candidate);
  const {surfaces, execution} = record;
  const hero = createElement("header", "artifact-hero");
  hero.append(createElement("p", "eyebrow", state.contentFormat), createElement("h2", "", pick(surfaces, ["title", "headline"], "当前成品")));
  const difference = candidateDifference(candidate);
  if (difference) hero.append(createElement("p", "", difference));
  ui.artifact.append(hero);
  appendTextSection(ui.artifact, "故事正文／内容概要", pick(surfaces, ["body", "content", "summary"], ""));
  appendListSection(ui.artifact, "口播、对白或旁白", pick(surfaces, ["spoken_lines", "spoken"], []));
  const deliverable = formatDeliverable(record);
  renderFormatSpecific(ui.artifact, state.contentFormat, deliverable, execution);
  appendTextSection(ui.artifact, "结尾与行动", pick(surfaces, ["CTA", "cta"], pick(execution, ["ending_and_action"], "")));
}

function renderFormatSpecific(parent, format, deliverable, execution) {
  if (!deliverable || typeof deliverable !== "object") return;
  if (format === "短视频") {
    const shots = asArray(pick(deliverable, ["shots", "storyboard"], []));
    if (shots.length) {
      const section = createElement("section", "result-block");
      section.append(createElement("h2", "", "逐镜分镜"));
      const wrap = createElement("div", "storyboard-wrap");
      const table = createElement("table", "storyboard");
      const head = createElement("thead");
      const headRow = createElement("tr");
      ["镜头", "时间与画面", "人物动作", "台词／旁白", "字幕", "机位与剪辑"].forEach((label) => headRow.append(createElement("th", "", label)));
      head.append(headRow);
      const body = createElement("tbody");
      shots.forEach((shot, index) => {
        const row = createElement("tr");
        row.append(
          createElement("td", "", String(index + 1)),
          createElement("td", "", [pick(shot, ["time_range", "time"], ""), pick(shot, ["visual", "picture"], "")].filter(Boolean).join("\n")),
          createElement("td", "", pick(shot, ["action", "character_action"], "")),
          createElement("td", "dialogue", pick(shot, ["audio", "dialogue", "voiceover"], "")),
          createElement("td", "", pick(shot, ["subtitle", "screen_text"], "")),
          createElement("td", "", [pick(shot, ["camera", "camera_direction"], ""), pick(shot, ["edit_note", "editing_note"], "")].filter(Boolean).join("；"))
        );
        body.append(row);
      });
      table.append(head, body);
      wrap.append(table);
      section.append(wrap);
      parent.append(section);
    }
    appendListSection(parent, "拍摄提示", pick(deliverable, ["shooting_notes"], []));
    appendListSection(parent, "剪辑提示", pick(deliverable, ["editing_notes"], []));
    return;
  }
  if (format === "图文") {
    appendTextSection(parent, "封面建议", pick(deliverable, ["cover_brief"], ""));
    const frames = asArray(pick(deliverable, ["frames"], []));
    if (frames.length) {
      const section = createElement("section", "result-block");
      section.append(createElement("h2", "", "图文页序"));
      const grid = createElement("div", "frame-grid");
      frames.forEach((frame, index) => {
        const card = createElement("article", "frame-card");
        card.append(createElement("strong", "", `第 ${index + 1} 页`), createElement("p", "", pick(frame, ["image_brief"], "")), createElement("p", "frame-copy", pick(frame, ["accompanying_copy", "copy"], "")));
        grid.append(card);
      });
      section.append(grid);
      parent.append(section);
    }
    appendListSection(parent, "版式建议", pick(deliverable, ["layout_notes"], []));
    return;
  }
  if (format === "直播内容包") {
    appendTextSection(parent, "直播主题", pick(deliverable, ["theme"], ""));
    appendTextSection(parent, "开场", pick(deliverable, ["opening"], ""));
    const segments = asArray(pick(deliverable, ["segments"], []));
    if (segments.length) {
      const section = createElement("section", "result-block");
      section.append(createElement("h2", "", "直播流程"));
      segments.forEach((segment, index) => {
        const card = createElement("article", "segment-card");
        card.append(createElement("strong", "", `${index + 1}. ${pick(segment, ["segment_title", "title"], "直播环节")}`));
        asArray(pick(segment, ["talking_points"], [])).forEach((point) => card.append(createElement("p", "", point)));
        const interaction = pick(segment, ["interaction_prompt"], "");
        if (interaction) card.append(createElement("small", "", `互动：${interaction}`));
        section.append(card);
      });
      parent.append(section);
    }
    appendListSection(parent, "互动问答", pick(deliverable, ["interaction_qa"], []));
    appendListSection(parent, "现场提醒", pick(deliverable, ["risk_reminders"], []));
    appendTextSection(parent, "收尾", pick(deliverable, ["closing"], ""));
    return;
  }
  if (format === "私域沟通内容") {
    appendTextSection(parent, "适用场景", pick(deliverable, ["applicable_scenario"], ""));
    const messages = asArray(pick(deliverable, ["messages"], []));
    if (messages.length) {
      const section = createElement("section", "result-block");
      section.append(createElement("h2", "", "沟通内容"));
      messages.forEach((message) => section.append(createElement("p", "message-copy", `${pick(message, ["channel"], "消息")}：${pick(message, ["copy", "message_text"], "")}`)));
      parent.append(section);
    }
    appendListSection(parent, "后续动作", pick(deliverable, ["follow_up_actions"], []));
    appendListSection(parent, "沟通边界", pick(deliverable, ["communication_boundaries"], []));
    return;
  }
  if (format === "门店线下物料") {
    appendTextSection(parent, "核心文案", pick(deliverable, ["core_copy"], ""));
    appendListSection(parent, "信息顺序", pick(deliverable, ["information_hierarchy"], []));
    appendListSection(parent, "版面或摆放建议", pick(deliverable, ["layout_or_placement_notes"], []));
    appendTextSection(parent, "行动提示", pick(deliverable, ["action_guidance"], ""));
    appendTextSection(parent, "使用边界", pick(deliverable, ["validity_boundary"], ""));
    return;
  }
  if (format === "培训与门店话术") {
    appendTextSection(parent, "培训目标", pick(deliverable, ["training_goal"], ""));
    appendListSection(parent, "培训提纲", pick(deliverable, ["outline"], []));
    appendListSection(parent, "练习", pick(deliverable, ["exercises"], []));
    const qa = asArray(pick(deliverable, ["situational_qa"], []));
    if (qa.length) {
      const section = createElement("section", "result-block");
      section.append(createElement("h2", "", "情境问答"));
      qa.forEach((row) => section.append(createElement("p", "message-copy", `问：${pick(row, ["question"], "")}\n答：${pick(row, ["suggested_answer", "answer"], "")}`)));
      parent.append(section);
    }
    appendListSection(parent, "可以这样说", pick(deliverable, ["allowed_phrasing"], []));
    appendListSection(parent, "不建议这样说", pick(deliverable, ["prohibited_phrasing"], []));
    return;
  }
  appendTextSection(parent, "陈列关系", pick(deliverable, ["arrangement_relationship"], ""));
  appendTextSection(parent, "空间层次", pick(deliverable, ["spatial_layers"], ""));
  appendTextSection(parent, "颜色关系", pick(deliverable, ["color_relationship"], ""));
  appendTextSection(parent, "现场提醒", pick(deliverable, ["availability_caution"], ""));
  appendListSection(parent, "拍摄角度", pick(deliverable, ["shooting_angles"], []));
}

function renderRevisionThread() {
  ui.revisionThread.replaceChildren();
  state.revisionMessages.slice(-5).forEach((message) => ui.revisionThread.append(createElement("p", `revision-message ${message.kind}`, message.text)));
}

async function selectCandidate(ordinal, quiet = false) {
  if (state.selectionConfirmed && state.confirmedOrdinal === ordinal) return true;
  state.selectedOrdinal = ordinal;
  state.selectionConfirmed = false;
  renderCandidateCards();
  renderArtifact();
  try {
    const value = await sendTask("选择候选", {message: "选择当前候选继续修改或使用。", candidate_number: ordinal});
    state.selectionConfirmed = true;
    state.confirmedOrdinal = ordinal;
    const version = state.versions[state.versionIndex];
    if (version) {
      version.selectedOrdinal = ordinal;
      version.selectionConfirmed = true;
      version.confirmedOrdinal = ordinal;
    }
    renderCandidateCards();
    if (!quiet) showToast(responseAnswer(value) || "已选择当前方案。");
    return true;
  } catch (error) {
    setStatus(error.message, "error");
    return false;
  }
}

function requireConfirmedCandidate() {
  if (!state.candidates.length || (state.selectionConfirmed && state.confirmedOrdinal === state.selectedOrdinal)) return true;
  setStatus("尚未选择候选：请先点选一份候选，再继续修改、复制或导出。", "warning");
  return false;
}

async function applyRevision() {
  const message = ui.revisionInput.value.trim();
  if (!message) {
    setStatus("请先说说想修改哪里。", "warning");
    ui.revisionInput.focus();
    return;
  }
  if (!requireConfirmedCandidate()) return;
  try {
    setBusy(true, "正在生成修改版…");
    state.revisionMessages.push({kind: "user", text: message});
    const value = await sendTask("把已有内容改好", {message, candidate_number: state.selectedOrdinal});
    const candidates = extractCandidates(value);
    const answer = responseAnswer(value);
    if (!candidates.length) throw new Error(answer || "本次修改没有生成可用成品，请换一种说法再试。");
    pushVersion(candidates, candidates.length ? "" : answer, candidates.some((candidate) => candidate.selected === true));
    state.revisionMessages.push({kind: "assistant", text: `第${state.versionIndex + 1}版已经生成，上一版仍可返回。`});
    ui.revisionInput.value = "";
    renderResult();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function copyResult() {
  if (!requireConfirmedCandidate()) return;
  const text = ui.artifact.innerText.trim();
  if (!text) {
    setStatus("当前没有可复制的成品。", "warning");
    return;
  }
  try {
    if (!navigator.clipboard?.writeText) throw new Error("clipboard unavailable");
    await navigator.clipboard.writeText(text);
    showToast("当前成品已复制。");
  } catch {
    setStatus("浏览器未允许自动复制，请选中成品文字后复制。", "warning");
  }
}

async function exportResult() {
  if (!requireConfirmedCandidate()) return;
  try {
    setBusy(true, "正在准备导出内容…");
    const value = await sendTask("导出", {message: "导出当前选择的内容。", candidate_number: state.selectedOrdinal});
    const uiState = value.ui_state || {};
    const downloadUrl = pick(value, ["download_url"], pick(uiState, ["download_url"], ""));
    if (downloadUrl) {
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.rel = "noopener";
      link.click();
      showToast("导出已经开始。");
      return;
    }
    const text = String(pick(value, ["export_text"], pick(uiState, ["export_text"], responseAnswer(value))));
    if (!text) throw new Error("服务端没有返回可导出的内容。");
    const blob = new Blob([text], {type: "text/plain;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const accountName = (state.currentAccount?.displayName || "笛语").replace(/[\\/:*?"<>|]/g, "-");
    link.href = url;
    link.download = `${accountName}-${state.contentFormat}${state.seriesMode === "SERIES" ? `-第${state.episodeIndex}集` : ""}.txt`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    showToast("内容已按服务端结果导出。");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function fillSimpleSelect(select, values) {
  select.replaceChildren();
  values.forEach((value) => select.add(new Option(typeof value === "string" ? value : String(pick(value, ["display_name", "label", "name"], "")), typeof value === "string" ? value : String(pick(value, ["value", "id", "display_name"], "")))));
}

function normalizeNamedRows(values, idKeys) {
  return asArray(values).map((item) => {
    if (typeof item === "string") return {id: item, label: item};
    return {
      ...item,
      id: String(pick(item, idKeys, pick(item, ["id", "value"], ""))),
      label: String(pick(item, ["display_name", "label", "name", "outward_account_name"], pick(item, idKeys, "")))
    };
  }).filter((item) => item.id && item.label);
}

function configureAdmin(source) {
  const organizations = normalizeNamedRows(pick(source, ["organizations"], pick(state.options, ["organizations"], [])), ["organization_id"]);
  const accountFamilies = normalizeNamedRows(pick(source, ["creatable_account_families", "account_families"], []), ["account_family", "family"]);
  const personaTypes = normalizeNamedRows(pick(source, ["persona_types", "personas"], []), ["persona_type"]);
  const personaTypesByFamily = pick(source, ["persona_types_by_family"], {});
  const organizationKindsByFamily = pick(source, ["organization_kinds_by_family"], {});
  const principals = normalizeNamedRows(pick(source, ["principals", "login_principals"], []), ["principal_id"]);
  if (organizations.length) state.admin.organizations = organizations;
  if (accountFamilies.length) state.admin.accountFamilies = accountFamilies;
  if (personaTypes.length) state.admin.personaTypes = personaTypes;
  if (personaTypesByFamily && typeof personaTypesByFamily === "object") {
    state.admin.personaTypesByFamily = Object.fromEntries(Object.entries(personaTypesByFamily).map(([family, rows]) => [family, normalizeNamedRows(rows, ["persona_type"])]));
  }
  if (organizationKindsByFamily && typeof organizationKindsByFamily === "object") {
    state.admin.organizationKindsByFamily = organizationKindsByFamily;
  }
  if (principals.length) state.admin.principals = principals;
  state.admin.enterpriseProfile = pick(source, ["enterprise_profile"], state.admin.enterpriseProfile);
  state.admin.organizationPeople = asArray(pick(source, ["organization_people"], state.admin.organizationPeople));
  state.admin.usage = asArray(pick(source, ["usage"], state.admin.usage));
  state.admin.systemStatus = pick(source, ["system_status"], state.admin.systemStatus);
  state.admin.contentProducts = asArray(pick(source, ["content_products"], state.admin.contentProducts));
  fillAdminFormOptions();
}

function fillAdminFormOptions() {
  const form = document.querySelector("#account-create-form");
  const mappings = [
    ["account_family", state.admin.accountFamilies],
  ];
  mappings.forEach(([name, rows]) => {
    const select = form.elements[name];
    select.replaceChildren(new Option("请选择", ""));
    rows.forEach((row) => select.add(new Option(row.label, row.id)));
  });
  refreshAdminPersonas();
  refreshAdminOrganizations();
}

function refreshAdminPersonas() {
  const form = document.querySelector("#account-create-form");
  const family = form.elements.account_family.value;
  const rows = state.admin.personaTypesByFamily[family] || state.admin.personaTypes;
  const select = form.elements.persona_type;
  select.replaceChildren(new Option("请选择", ""));
  rows.forEach((row) => select.add(new Option(row.label, row.id)));
}

function refreshAdminOrganizations() {
  const form = document.querySelector("#account-create-form");
  const family = form.elements.account_family.value;
  const allowedKinds = asArray(state.admin.organizationKindsByFamily[family]);
  const rows = family
    ? state.admin.organizations.filter((row) => allowedKinds.includes(row.organization_kind))
    : [];
  const select = form.elements.organization_id;
  const previous = select.value;
  select.replaceChildren(new Option("请选择", ""));
  rows.forEach((row) => select.add(new Option(row.label, row.id)));
  if (rows.some((row) => row.id === previous)) select.value = previous;
  refreshAdminPrincipals();
}

function refreshAdminPrincipals() {
  const form = document.querySelector("#account-create-form");
  const organizationId = form.elements.organization_id.value;
  const rows = organizationId
    ? state.admin.principals.filter((row) => asArray(row.organization_scope_ids).includes(organizationId))
    : [];
  const select = form.elements.principal_id;
  const previous = select.value;
  select.replaceChildren(new Option("请选择", ""));
  rows.forEach((row) => select.add(new Option(row.label, row.id)));
  if (rows.some((row) => row.id === previous)) select.value = previous;
}

async function loadAdminAccounts() {
  try {
    setStatus("正在读取企业管理数据…");
    const value = await requestJson("/v1/admin/accounts");
    const source = value.account_matrix || value.admin || value;
    state.admin.accounts = asArray(pick(source, ["accounts", "items"], []));
    configureAdmin(source);
    renderAdminWorkspace();
    setStatus("");
  } catch (error) {
    setStatus(error.message, "error");
    renderAdminWorkspace();
  }
}

function localDateTime(value) {
  if (!value) return "暂无新版本使用记录";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN", {hour12: false});
}

function renderAdminWorkspace() {
  renderEnterpriseProfile();
  renderOrganizationPeople();
  renderAdminMatrix();
  renderAdminUsage();
  renderSystemStatus();
}

function renderEnterpriseProfile() {
  const root = document.querySelector("#admin-enterprise-profile");
  const profile = state.admin.enterpriseProfile || {};
  root.replaceChildren();
  const facts = [
    ["当前企业", pick(profile, ["display_name"], "暂不可用")],
    ["资料性质", profile.simulation_only ? "模拟验收企业" : "已授权企业资料"],
    ["资料来源", pick(profile, ["data_source_display_name"], "暂不可用")],
    ["资料版本", pick(profile, ["data_version"], "暂不可用")],
    ["导入状态", pick(profile, ["import_status_display_name"], "暂不可用")],
    ["最后更新时间", localDateTime(pick(profile, ["last_updated_at"], null))]
  ];
  facts.forEach(([label, value]) => {
    const row = createElement("div");
    row.append(createElement("dt", "", label), createElement("dd", "", value));
    root.append(row);
  });
  const products = document.querySelector("#admin-content-products");
  products.replaceChildren();
  state.admin.contentProducts.forEach((product) => products.append(createElement("span", "", product)));
}

function renderOrganizationPeople() {
  const root = document.querySelector("#admin-organization-list");
  root.replaceChildren();
  if (!state.admin.organizationPeople.length) {
    root.append(createElement("p", "empty-state", "当前没有可展示的组织与人员。"));
    return;
  }
  state.admin.organizationPeople.forEach((organization) => {
    const card = createElement("article", "organization-card");
    const header = createElement("header");
    header.append(
      createElement("h3", "", pick(organization, ["display_name"], "未命名组织")),
      createElement("span", "", `${pick(organization, ["organization_kind_display_name"], "组织")} · ${organization.status === "ACTIVE" ? "使用中" : "已停用"}`)
    );
    card.append(header);
    const people = asArray(organization.login_principals);
    const list = createElement("ul");
    if (!people.length) {
      list.append(createElement("li", "", "当前没有登录使用人。"));
    } else {
      people.forEach((person) => {
        const accounts = asArray(person.bound_content_accounts).map((account) => pick(account, ["outward_account_name"], "")).filter(Boolean);
        const item = createElement("li");
        item.append(
          createElement("strong", "", pick(person, ["display_name"], "未命名使用人")),
          createElement("span", "", ` · ${pick(person, ["business_role_name"], "岗位未标注")} · ${person.status === "ACTIVE" ? "可登录" : "已停用"} · ${accounts.length ? `已绑定：${accounts.join("、")}` : "未绑定内容账号"}`)
        );
        list.append(item);
      });
    }
    card.append(list);
    root.append(card);
  });
}

function renderAdminUsage() {
  const root = document.querySelector("#admin-usage");
  root.replaceChildren();
  if (!state.admin.usage.length) {
    root.append(createElement("p", "empty-state", "当前没有可展示的使用记录。"));
    return;
  }
  const wrap = createElement("div", "admin-table-wrap");
  const table = createElement("table", "admin-table");
  const head = createElement("thead");
  const headRow = createElement("tr");
  ["对外账号", "账号族", "所属组织", "请求次数", "最近活动", "状态"].forEach((label) => headRow.append(createElement("th", "", label)));
  head.append(headRow);
  const body = createElement("tbody");
  state.admin.usage.forEach((usage) => {
    const count = Number(pick(usage, ["activity_count"], 0));
    const row = createElement("tr");
    row.append(
      createElement("td", "account-name-cell", pick(usage, ["outward_account_name"], "—")),
      createElement("td", "", pick(usage, ["account_family_display_name"], "—")),
      createElement("td", "", pick(usage, ["organization_display_name"], "—")),
      createElement("td", "", count ? String(count) : "暂无新版本记录"),
      createElement("td", "", localDateTime(pick(usage, ["last_activity_at"], null))),
      createElement("td", "", usage.status === "ACTIVE" ? "使用中" : "已停用")
    );
    body.append(row);
  });
  table.append(head, body);
  wrap.append(table);
  root.append(wrap);
}

function renderSystemStatus() {
  const root = document.querySelector("#admin-system-status");
  const status = state.admin.systemStatus || {};
  const services = asArray(pick(status, ["services"], []));
  root.replaceChildren();
  if (!services.length) {
    root.append(createElement("p", "empty-state", "系统状态暂时无法读取，请稍后重试。"));
    return;
  }
  services.forEach((service) => {
    const available = Boolean(pick(service, ["available"], false));
    const card = createElement("div", `system-status-card${available ? "" : " unavailable"}`);
    card.append(
      createElement("strong", "", pick(service, ["label"], "服务")),
      createElement("span", "", available ? "可用" : "稍后重试")
    );
    root.append(card);
  });
  root.append(createElement("p", "system-status-note", `检查时间：${localDateTime(pick(status, ["checked_at"], null))}`));
}

function renderAdminMatrix() {
  const root = document.querySelector("#account-matrix");
  root.replaceChildren();
  document.querySelector("#admin-account-count").textContent = `${state.admin.accounts.length} 个内容账号`;
  if (!state.admin.accounts.length) {
    root.append(createElement("p", "empty-state", "当前没有可展示的内容账号。"));
    return;
  }
  const tableWrap = createElement("div", "admin-table-wrap");
  const table = createElement("table", "admin-table");
  const head = createElement("thead");
  const headRow = createElement("tr");
  ["对外账号", "账号族", "长期人设", "所属组织", "登录使用人", "状态", "操作"].forEach((label) => headRow.append(createElement("th", "", label)));
  head.append(headRow);
  const body = createElement("tbody");
  state.admin.accounts.forEach((account) => {
    const row = createElement("tr");
    const id = String(pick(account, ["account_id", "id"], ""));
    const status = String(pick(account, ["status", "state"], "ACTIVE"));
    row.append(
      createElement("td", "account-name-cell", pick(account, ["outward_account_name", "display_name", "name"], "—")),
      createElement("td", "", pick(account, ["account_family_display_name", "account_family", "family"], "—")),
      createElement("td", "", pick(account, ["persona_type_display_name", "persona_type", "persona"], "—")),
      createElement("td", "", pick(account, ["organization_display_name", "organization_name"], "—")),
      createElement("td", "", pick(account, ["principal_display_name", "login_user_display_name", "principal_name"], "—")),
      createElement("td", "", status === "ACTIVE" ? "使用中" : "已停用")
    );
    const actionCell = createElement("td");
    const canDisable = Boolean(pick(account, ["can_disable"], status === "ACTIVE")) && id;
    if (canDisable) {
      const button = createElement("button", "quiet-button", "停用");
      button.type = "button";
      button.dataset.disableAccount = id;
      button.dataset.accountName = String(pick(account, ["outward_account_name", "display_name", "name"], "这个账号"));
      actionCell.append(button);
    } else actionCell.textContent = "—";
    row.append(actionCell);
    body.append(row);
  });
  table.append(head, body);
  tableWrap.append(table);
  root.append(tableWrap);
}

async function createAdminAccount(event) {
  event.preventDefault();
  const formElement = event.currentTarget;
  const form = new FormData(formElement);
  const body = Object.fromEntries(form.entries());
  try {
    setBusy(true, "正在创建内容账号…");
    const value = await requestJson("/v1/admin/accounts", {method: "POST", body: JSON.stringify(body)});
    showToast(responseAnswer(value) || "内容账号已创建。");
    formElement.reset();
    setHidden(formElement, true);
    await loadAdminAccounts();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function disableAdminAccount(accountId, accountName) {
  if (!window.confirm(`确定停用“${accountName}”吗？绑定使用人下次进入后将不再看到它。`)) return;
  try {
    setBusy(true, "正在停用内容账号…");
    const value = await requestJson(`/v1/admin/accounts/${encodeURIComponent(accountId)}/disable`, {method: "POST"});
    showToast(responseAnswer(value) || "内容账号已停用。");
    await loadAdminAccounts();
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

ui.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  ui.loginFeedback.textContent = "正在登录…";
  try {
    const value = await requestJson(
      "/login",
      {
        method: "POST",
        body: JSON.stringify({username: form.get("username"), password: form.get("password")})
      },
      "系统暂时无法完成登录，请稍后重试。"
    );
    ui.loginFeedback.textContent = "";
    activateWorkspace(value);
  } catch (error) {
    ui.loginFeedback.textContent = error.message;
  }
});

document.querySelector("#logout").addEventListener("click", async () => {
  try {
    const value = await requestJson("/logout", {method: "POST"});
    enterLoginState(responseAnswer(value) || "已安全退出，请重新登录。");
  } catch (error) {
    if (error.errorType !== "SESSION_EXPIRED") setStatus(error.message, "error");
  }
});

document.querySelector("#account-switcher").addEventListener("change", (event) => {
  state.currentAccount = state.accounts.find((account) => account.id === event.target.value) || state.currentAccount;
  renderIdentity();
  resetCreation();
});

ui.idea.addEventListener("input", () => {
  state.idea = ui.idea.value;
  if (state.selectedDirection && state.idea.trim() !== state.selectedDirection.prompt) state.selectedDirection = null;
});
document.querySelector("#think-with-me").addEventListener("click", () => requestAngles(state.startMode));
document.querySelector("#send-chat").addEventListener("click", async () => {
  state.idea = ui.idea.value.trim();
  if (!state.idea) {
    setStatus("请先说一句想聊什么。", "warning");
    ui.idea.focus();
    return;
  }
  try {
    setBusy(true, "正在回应…");
    const value = await sendTask("随便聊聊", {message: state.idea, series_mode: "SINGLE", episode_index: 1});
    ui.homeResponse.textContent = responseAnswer(value);
    setHidden(ui.homeResponse, false);
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
});

document.querySelectorAll("[data-start-mode]").forEach((button) => button.addEventListener("click", () => {
  state.startMode = button.dataset.startMode;
  document.querySelectorAll("[data-start-mode]").forEach((row) => row.classList.toggle("selected", row === button));
  if (state.startMode === "improve") ui.idea.placeholder = "贴入或概括旧内容，再点“陪我想”。";
  else if (state.startMode === "make") ui.idea.placeholder = "说说这件事或你手里的资料，再点“陪我想”。";
  else ui.idea.placeholder = state.currentAccount?.placeholder || "一个片段、问题或模糊想法都可以。";
  ui.idea.focus();
}));
document.querySelectorAll("[data-example-direction]").forEach((button) => button.addEventListener("click", () => {
  state.exampleDirection = button.dataset.exampleDirection;
  document.querySelectorAll("[data-example-direction]").forEach((row) => row.classList.toggle("selected", row === button));
  showToast(`已选“${button.dataset.exampleDirection}”，请继续说你的本次主题。`);
  ui.idea.focus();
}));
document.querySelector("#quick-speaker").addEventListener("change", (event) => {
  state.speakerRoleName = event.target.value || state.currentAccount?.speakerRole || null;
});
document.querySelector("#quick-material").addEventListener("change", (event) => {
  state.materialKinds = event.target.value ? [event.target.value] : [];
});
document.querySelector("#quick-format").addEventListener("change", (event) => {
  state.contentFormat = event.target.value || state.currentAccount?.recommendedFormat || "短视频";
  renderIdentity();
});
document.querySelector("#quick-goal").addEventListener("change", (event) => {
  state.businessGoal = event.target.value || null;
});
document.querySelector("#content-product-search").addEventListener("change", (event) => {
  const direction = event.target.value.trim();
  if (!direction) return;
  state.exampleDirection = direction;
  showToast(`已选择“${direction}”，系统会结合你的主题匹配后台内容产品。`);
  ui.idea.focus();
});
ui.directions.addEventListener("click", (event) => {
  const button = event.target.closest("[data-direction-index]");
  if (!button) return;
  requestAngles("make", accountDirections()[Number(button.dataset.directionIndex)]);
});
ui.angles.addEventListener("click", (event) => {
  const button = event.target.closest("[data-angle-index]");
  if (!button) return;
  state.selectedAngle = Number(button.dataset.angleIndex);
  renderAngles();
});
document.querySelector("#confirm-angle").addEventListener("click", () => {
  state.detail = ui.angleDetail.value.trim();
  setStep("confirm");
});
document.querySelector("#confirm-theme").addEventListener("input", (event) => {
  state.idea = event.target.value;
  ui.idea.value = state.idea;
});
document.querySelectorAll("[data-back-step]").forEach((button) => button.addEventListener("click", () => setStep(button.dataset.backStep)));
document.querySelectorAll("[data-step]").forEach((button) => button.addEventListener("click", () => {
  const index = STEP_ORDER.indexOf(button.dataset.step);
  if (index <= state.maxStep) setStep(button.dataset.step);
}));
document.querySelectorAll("[data-series-mode]").forEach((button) => button.addEventListener("click", () => chooseSeriesMode(button.dataset.seriesMode)));
document.querySelector("#format-options").addEventListener("click", (event) => {
  const button = event.target.closest("[data-format]");
  if (!button) return;
  state.contentFormat = button.dataset.format;
  renderIdentity();
  renderConfirm();
});
document.querySelector("#platform-select").addEventListener("change", (event) => { state.platform = event.target.value; renderConfirm(); });
document.querySelector("#duration-select").addEventListener("change", (event) => { state.duration = event.target.value; renderConfirm(); });
document.querySelector("#audience-input").addEventListener("input", (event) => {
  state.primaryAudience = event.target.value;
  document.querySelector("#confirmed-audience").textContent = state.primaryAudience || "由系统建议";
});
document.querySelector("#feeling-select").addEventListener("change", (event) => { state.expressionFeeling = event.target.value; });
document.querySelector("#generate").addEventListener("click", () => generateContent());
ui.candidates.addEventListener("click", (event) => {
  const button = event.target.closest("[data-candidate-ordinal]");
  if (button) selectCandidate(Number(button.dataset.candidateOrdinal));
});
document.querySelector("#apply-revision").addEventListener("click", applyRevision);
document.querySelector("#previous-version").addEventListener("click", () => {
  if (state.versionIndex > 0) loadVersion(state.versionIndex - 1);
});
document.querySelector("#change-angle").addEventListener("click", () => setStep("angles"));
document.querySelector("#change-format").addEventListener("click", () => setStep("confirm"));
document.querySelector("#next-episode").addEventListener("click", () => {
  const nextEpisode = state.episodeIndex + 1;
  if (state.episodeWorkspaces[String(nextEpisode)]) showEpisode(nextEpisode);
  else generateContent({nextEpisode: true});
});
document.querySelector("#episode-history").addEventListener("click", (event) => {
  const button = event.target.closest("[data-episode-index]");
  if (button) showEpisode(Number(button.dataset.episodeIndex));
});
document.querySelector("#copy-result").addEventListener("click", copyResult);
document.querySelector("#export-result").addEventListener("click", exportResult);

document.querySelector("#open-account-create").addEventListener("click", () => setHidden(document.querySelector("#account-create-form"), false));
document.querySelector("#cancel-account-create").addEventListener("click", () => setHidden(document.querySelector("#account-create-form"), true));
document.querySelector("#account-create-form").addEventListener("submit", createAdminAccount);
document.querySelector("#account-create-form").elements.account_family.addEventListener("change", () => {
  refreshAdminPersonas();
  refreshAdminOrganizations();
});
document.querySelector("#account-create-form").elements.organization_id.addEventListener("change", refreshAdminPrincipals);
document.querySelector("#account-matrix").addEventListener("click", (event) => {
  const button = event.target.closest("[data-disable-account]");
  if (button) disableAdminAccount(button.dataset.disableAccount, button.dataset.accountName);
});
document.querySelectorAll("[data-admin-tab]").forEach((button) => button.addEventListener("click", () => {
  document.querySelectorAll("[data-admin-tab]").forEach((row) => row.classList.toggle("selected", row === button));
  document.querySelectorAll("[data-admin-panel]").forEach((panel) => setHidden(panel, panel.dataset.adminPanel !== button.dataset.adminTab));
}));

updateProgress();
}
