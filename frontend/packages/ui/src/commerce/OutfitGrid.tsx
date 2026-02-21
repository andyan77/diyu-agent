"use client";

/**
 * OutfitGrid: grid display for curated outfit combinations.
 *
 * Task card: FW3-3
 * Renders a collection of outfit items in a responsive grid layout.
 */

interface OutfitItem {
  id: string;
  name: string;
  imageUrl?: string;
  category: string;
}

interface OutfitGridProps {
  title: string;
  items: OutfitItem[];
  onItemSelect?: (id: string) => void;
}

export function OutfitGrid({ title, items, onItemSelect }: OutfitGridProps) {
  return (
    <div data-testid="outfit-grid" style={{ marginBottom: 24 }}>
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
          data-testid="outfit-empty"
          style={{ padding: 32, textAlign: "center", color: "#9ca3af" }}
        >
          No items in this outfit
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))",
          gap: 12,
        }}
      >
        {items.map((item) => (
          <div
            key={item.id}
            data-testid={`outfit-item-${item.id}`}
            onClick={() => onItemSelect?.(item.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") onItemSelect?.(item.id);
            }}
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              overflow: "hidden",
              cursor: onItemSelect ? "pointer" : "default",
              background: "white",
            }}
          >
            <div
              style={{
                width: "100%",
                height: 150,
                background: item.imageUrl
                  ? `url(${item.imageUrl}) center/cover`
                  : "#f3f4f6",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#9ca3af",
                fontSize: 12,
              }}
            >
              {!item.imageUrl && item.category}
            </div>
            <div style={{ padding: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{item.name}</div>
              <div style={{ fontSize: 11, color: "#9ca3af" }}>{item.category}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
