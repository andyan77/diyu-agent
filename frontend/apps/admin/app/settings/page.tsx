"use client";

/**
 * Organization settings management page.
 *
 * Task card: FA3-3
 * Manages org_settings: model access, budget limits, feature flags, branding.
 * API: GET/PUT /api/v1/admin/settings (via org_settings table)
 */

import { useCallback, useState } from "react";

interface OrgSettings {
  org_name: string;
  org_tier: string;
  default_model: string;
  allowed_models: string[];
  budget_monthly_tokens: number;
  max_conversation_length: number;
  features: {
    knowledge_enabled: boolean;
    skill_enabled: boolean;
    multimodal_enabled: boolean;
    export_enabled: boolean;
  };
  branding: {
    primary_color: string;
    logo_url: string;
  };
}

const DEFAULT_SETTINGS: OrgSettings = {
  org_name: "Demo Organization",
  org_tier: "brand_hq",
  default_model: "gpt-4o",
  allowed_models: ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"],
  budget_monthly_tokens: 1_000_000,
  max_conversation_length: 100,
  features: {
    knowledge_enabled: true,
    skill_enabled: true,
    multimodal_enabled: false,
    export_enabled: true,
  },
  branding: {
    primary_color: "#3b82f6",
    logo_url: "",
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<OrgSettings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  const handleSave = useCallback(() => {
    // Placeholder: would call PUT /api/v1/admin/settings
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }, []);

  const updateFeature = (key: keyof OrgSettings["features"], value: boolean) => {
    setSettings((prev) => ({
      ...prev,
      features: { ...prev.features, [key]: value },
    }));
  };

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      <h1
        data-testid="settings-title"
        style={{ fontSize: 20, fontWeight: 600, marginBottom: 24 }}
      >
        Organization Settings
      </h1>

      {/* General */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: "#374151" }}>
          General
        </h2>
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Organization Name
            </label>
            <input
              data-testid="org-name-input"
              type="text"
              value={settings.org_name}
              onChange={(e) => setSettings((prev) => ({ ...prev, org_name: e.target.value }))}
              aria-label="Organization name"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 6,
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Tier
            </label>
            <select
              data-testid="org-tier-select"
              value={settings.org_tier}
              onChange={(e) => setSettings((prev) => ({ ...prev, org_tier: e.target.value }))}
              aria-label="Organization tier"
              style={{
                padding: "8px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 6,
              }}
            >
              <option value="platform">Platform</option>
              <option value="brand_hq">Brand HQ</option>
              <option value="region">Region</option>
              <option value="store">Store</option>
            </select>
          </div>
        </div>
      </section>

      {/* Model access */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: "#374151" }}>
          Model Access
        </h2>
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label htmlFor="default-model-select" style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Default Model
            </label>
            <select
              id="default-model-select"
              data-testid="default-model-select"
              value={settings.default_model}
              onChange={(e) => setSettings((prev) => ({ ...prev, default_model: e.target.value }))}
              aria-label="Default model"
              style={{
                padding: "8px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 6,
              }}
            >
              {settings.allowed_models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="budget-input" style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Monthly Token Budget
            </label>
            <input
              id="budget-input"
              data-testid="budget-input"
              type="number"
              value={settings.budget_monthly_tokens}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  budget_monthly_tokens: Number(e.target.value) || 0,
                }))
              }
              aria-label="Monthly token budget"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 6,
              }}
            />
          </div>
        </div>
      </section>

      {/* Feature flags */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: "#374151" }}>
          Features
        </h2>
        <div style={{ display: "grid", gap: 8 }}>
          {(
            Object.entries(settings.features) as [keyof OrgSettings["features"], boolean][]
          ).map(([key, enabled]) => (
            <label
              key={key}
              htmlFor={`feature-${key}`}
              data-testid={`feature-${key}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              <input
                id={`feature-${key}`}
                type="checkbox"
                checked={enabled}
                onChange={(e) => updateFeature(key, e.target.checked)}
              />
              {key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </label>
          ))}
        </div>
      </section>

      {/* Branding */}
      <section style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, color: "#374151" }}>
          Branding
        </h2>
        <div style={{ display: "grid", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Primary Color
            </label>
            <input
              data-testid="primary-color-input"
              type="color"
              value={settings.branding.primary_color}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  branding: { ...prev.branding, primary_color: e.target.value },
                }))
              }
              aria-label="Primary color"
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Logo URL
            </label>
            <input
              data-testid="logo-url-input"
              type="text"
              value={settings.branding.logo_url}
              onChange={(e) =>
                setSettings((prev) => ({
                  ...prev,
                  branding: { ...prev.branding, logo_url: e.target.value },
                }))
              }
              placeholder="https://..."
              aria-label="Logo URL"
              style={{
                width: "100%",
                padding: "8px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 6,
              }}
            />
          </div>
        </div>
      </section>

      {/* Save button */}
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button
          data-testid="save-settings-btn"
          onClick={handleSave}
          style={{
            padding: "10px 24px",
            background: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: 500,
          }}
        >
          Save Settings
        </button>
        {saved && (
          <span data-testid="save-success" style={{ color: "#22c55e", fontSize: 13 }}>
            Settings saved successfully
          </span>
        )}
      </div>
    </div>
  );
}
