"use strict";

const loginSection = document.querySelector("#login-section");
const workbench = document.querySelector("#workbench");
const resultSection = document.querySelector("#result-section");
const output = document.querySelector("#output");
const taskForm = document.querySelector("#task-form");
const productionFields = document.querySelector("#production-fields");
const candidateFields = document.querySelector("#candidate-fields");
const advancedFields = document.querySelector("#advanced-fields");
const quickPrompts = document.querySelector("#quick-prompts");
let options = null;
const portalBase = window.location.pathname.startsWith("/apps") ? "/apps" : "";

function endpoint(path) {
  return `${portalBase}${path}`;
}

const operationLabels = [
  "随便聊聊", "找点灵感", "直接做内容", "把已有内容改好", "继续一个系列",
  "选择候选", "审核", "导出", "查看来源", "提交反馈"
];

const promptSuggestions = [
  {label: "从一个真实细节开始", text: "我只有一个细节，请先帮我找到最适合的内容方向。"},
  {label: "讲清一个选择问题", text: "我想讲清一个用户选择问题，请先问我最关键的一项材料。"},
  {label: "做账号范围介绍", text: "做一份账号介绍，只说明这个账号可以讲什么和内容边界。"}
];

function fillSelect(name, values, includeBlank = false) {
  const select = taskForm.elements[name];
  select.replaceChildren();
  if (includeBlank) select.add(new Option("由系统建议", ""));
  for (const value of values) {
    select.add(new Option(value, value));
  }
}

function updateRoleAndColumn() {
  const account = taskForm.elements.account_display_name.value;
  const storyline = taskForm.elements.storyline_name.value;
  fillSelect("speaker_role_name", options.roles_by_account[account] || [], true);
  fillSelect("column_name", options.columns_by_storyline[storyline] || [], true);
}

function updateTaskMode() {
  const operation = taskForm.elements.operation.value;
  const makesContent = ["直接做内容", "把已有内容改好", "继续一个系列"].includes(operation);
  const needsCandidate = ["选择候选", "把已有内容改好"].includes(operation);
  productionFields.classList.toggle("hidden", !makesContent);
  advancedFields.classList.toggle("hidden", !makesContent);
  candidateFields.classList.toggle("hidden", !needsCandidate);
  quickPrompts.replaceChildren();
  if (!["找点灵感", "直接做内容", "继续一个系列"].includes(operation)) return;
  for (const suggestion of promptSuggestions) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "suggestion";
    button.textContent = suggestion.label;
    button.title = suggestion.text;
    button.addEventListener("click", () => {
      taskForm.elements.message.value = suggestion.text;
      taskForm.elements.message.focus();
    });
    quickPrompts.append(button);
  }
}

function activateWorkbench(value) {
  options = value;
  fillSelect("operation", operationLabels);
  fillSelect("account_display_name", value.content_accounts);
  fillSelect("topic_label", value.topics, true);
  fillSelect("target_platform", value.platforms);
  fillSelect("duration_label", value.durations);
  fillSelect("expression_feeling", value.feelings);
  fillSelect("content_format", value.content_formats);
  fillSelect("storyline_name", value.storylines, true);
  fillSelect("organization_level", value.organization_levels, true);
  fillSelect("content_identity", value.content_identities, true);
  fillSelect("long_term_storyline", value.long_term_storylines, true);
  fillSelect("content_direction", value.content_directions, true);
  fillSelect("business_goal", value.business_goals, true);
  fillSelect("expression_method", value.expression_methods, true);
  const materials = document.querySelector("#materials");
  materials.replaceChildren();
  for (const kind of value.material_kinds) {
    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.name = "existing_material_kinds";
    checkbox.value = kind;
    label.append(checkbox, document.createTextNode(kind));
    materials.append(label);
  }
  updateRoleAndColumn();
  updateTaskMode();
  loginSection.classList.add("hidden");
  workbench.classList.remove("hidden");
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const response = await fetch(endpoint("/login"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      credentials: "same-origin",
      body: JSON.stringify({username: form.get("username"), password: form.get("password")})
    });
    const value = await response.json();
    if (!response.ok) { output.textContent = value.user_visible_text; resultSection.classList.remove("hidden"); return; }
    activateWorkbench(value.options);
  } catch {
    output.textContent = "系统暂时无法完成登录，请稍后重试。";
    resultSection.classList.remove("hidden");
  }
});

taskForm.elements.account_display_name.addEventListener("change", updateRoleAndColumn);
taskForm.elements.storyline_name.addEventListener("change", updateRoleAndColumn);
taskForm.elements.operation.addEventListener("change", updateTaskMode);

taskForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const send = document.querySelector("#send");
  send.disabled = true;
  output.textContent = "处理中……";
  resultSection.classList.remove("hidden");
  const form = new FormData(taskForm);
  const body = Object.fromEntries(form.entries());
  body.candidate_number = body.candidate_number ? Number(body.candidate_number) : null;
  body.localization_allowed = taskForm.elements.localization_allowed.checked;
  body.continue_previous = body.operation === "继续一个系列";
  body.existing_material_kinds = form.getAll("existing_material_kinds");
  for (const key of [
    "topic_label", "primary_audience", "content_goal", "key_takeaway",
    "speaker_role_name", "storyline_name", "column_name", "organization_level",
    "content_identity", "long_term_storyline", "content_direction", "business_goal",
    "expression_method"
  ]) {
    if (!body[key]) body[key] = null;
  }
  try {
    const response = await fetch(endpoint("/v1/portal/chat"), {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-Diyu-Portal": "same-origin-v1"},
      credentials: "same-origin",
      body: JSON.stringify(body)
    });
    const value = await response.json();
    output.textContent = response.ok ? value.answer : value.user_visible_text;
  } catch {
    output.textContent = "系统暂时无法完成请求，请稍后重试。";
  } finally {
    send.disabled = false;
  }
});

document.querySelector("#logout").addEventListener("click", async () => {
  await fetch(endpoint("/logout"), {method: "POST", headers: {"X-Diyu-Portal": "same-origin-v1"}, credentials: "same-origin"});
  window.location.reload();
});
