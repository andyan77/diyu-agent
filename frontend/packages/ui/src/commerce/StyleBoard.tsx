"use client";

/**
 * StyleBoard: mood board / style inspiration panel.
 *
 * Task card: FW3-3
 * Displays curated style inspirations with tags and descriptions.
 */

interface StyleItem {
  id: string;
  title: string;
  description: string;
  imageUrl?: string;
  tags: string[];
}

interface StyleBoardProps {
  title: string;
  items: StyleItem[];
  onItemSelect?: (id: string) => void;
}

export function StyleBoard({ title, items, onItemSelect }: StyleBoardProps) {
  return (
    <div data-testid="style-board" style={{ marginBottom: 24 }}>
      <h3
        style={{
          fontSize: 16,
          fontWeight: 600,
          marginBottom: 12,
          color: "#111827",
        }}
      >
        {title}
      </h3>

      {items.length === 0 && (
        <div
          data-testid="style-empty"
          style={{ padding: 32, textAlign: "center", color: "#9ca3af" }}
        >
          No style inspirations yet
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))",
          gap: 16,
        }}
      >
        {items.map((item) => (
          <div
            key={item.id}
            data-testid={`style-item-${item.id}`}
            onClick={() => onItemSelect?.(item.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onItemSelect?.(item.id);
            }}
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: 12,
              overflow: "hidden",
              cursor: onItemSelect ? "pointer" : "default",
              background: "white",
            }}
          >
            <div
              style={{
                width: "100%",
                height: 180,
                background: item.imageUrl
                  ? `url(${item.imageUrl}) center/cover`
                  : "linear-gradient(135deg, #f3f4f6, #e5e7eb)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#9ca3af",
                fontSize: 14,
              }}
            >
              {!item.imageUrl && item.title}
            </div>
            <div style={{ padding: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
                {item.title}
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "#6b7280",
                  lineHeight: 1.4,
                  marginBottom: 8,
                }}
              >
                {item.description.slice(0, 100)}
                {item.description.length > 100 ? "..." : ""}
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {item.tags.map((tag) => (
                  <span
                    key={tag}
                    style={{
                      fontSize: 10,
                      padding: "2px 6px",
                      background: "#eff6ff",
                      color: "#3b82f6",
                      borderRadius: 4,
                    }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
