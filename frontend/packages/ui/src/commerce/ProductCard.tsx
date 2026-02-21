"use client";

/**
 * ProductCard: individual product display card.
 *
 * Task card: FW3-3
 * Part of the commerce component library for knowledge-driven product display.
 */

interface ProductCardProps {
  id: string;
  name: string;
  price: number;
  currency?: string;
  imageUrl?: string;
  brand?: string;
  category?: string;
  onSelect?: (id: string) => void;
}

export function ProductCard({
  id,
  name,
  price,
  currency = "CNY",
  imageUrl,
  brand,
  category,
  onSelect,
}: ProductCardProps) {
  const formattedPrice = new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
  }).format(price);

  return (
    <div
      data-testid={`product-card-${id}`}
      onClick={() => onSelect?.(id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") onSelect?.(id);
      }}
      aria-label={`Product: ${name}`}
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 8,
        overflow: "hidden",
        cursor: onSelect ? "pointer" : "default",
        background: "white",
        transition: "box-shadow 0.15s",
      }}
    >
      {/* Image placeholder */}
      <div
        data-testid="product-image"
        style={{
          width: "100%",
          height: 200,
          background: imageUrl ? `url(${imageUrl}) center/cover` : "#f3f4f6",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#9ca3af",
          fontSize: 13,
        }}
      >
        {!imageUrl && "No image"}
      </div>

      {/* Info */}
      <div style={{ padding: 12 }}>
        {brand && (
          <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 2 }}>{brand}</div>
        )}
        <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>{name}</div>
        {category && (
          <div
            style={{
              fontSize: 11,
              color: "#9ca3af",
              background: "#f3f4f6",
              display: "inline-block",
              padding: "1px 6px",
              borderRadius: 3,
              marginBottom: 6,
            }}
          >
            {category}
          </div>
        )}
        <div style={{ fontSize: 16, fontWeight: 600, color: "#ef4444" }}>
          {formattedPrice}
        </div>
      </div>
    </div>
  );
}
