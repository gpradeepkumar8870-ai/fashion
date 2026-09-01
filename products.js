/* =========================================================
   StyleHub - Shared product card rendering + wishlist toggle
   Used by: home page, products listing, wishlist page
   ========================================================= */

function shRenderProductCard(p) {
  const img = p.primary_image || "/static/images/no-image.png";
  const hasDiscount = p.discount_price && p.discount_price < p.price;
  const colorDots = (p.available_colors || []).slice(0, 4).map(c =>
    `<span class="sh-color-dot" style="background:${shColorToHex(c)}" title="${SH.escapeHtml(c)}"></span>`
  ).join(" ");

  return `
  <div class="col-6 col-md-4 col-lg-3 mb-4 sh-product-col" data-product-id="${p.id}">
    <div class="sh-product-card">
      <a href="/products/${p.slug}" class="text-decoration-none text-dark">
        <div class="sh-img-wrap">
          <img src="${img}" alt="${SH.escapeHtml(p.name)}" loading="lazy">
          ${hasDiscount ? `<span class="sh-badge-discount">${p.discount_percent}% OFF</span>` : ""}
          ${p.is_bestseller ? `<span class="sh-badge-bestseller">Bestseller</span>` : ""}
        </div>
      </a>
      <button class="sh-wishlist-btn" data-product-id="${p.id}" title="Add to wishlist">
        <i class="bi bi-heart"></i>
      </button>
      <div class="sh-body">
        <div class="sh-brand">${SH.escapeHtml(p.brand ? p.brand.name : "")}</div>
        <a href="/products/${p.slug}" class="text-decoration-none text-dark">
          <div class="sh-name">${SH.escapeHtml(p.name)}</div>
        </a>
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="sh-price">${SH.fmtPrice(p.effective_price)}</span>
          ${hasDiscount ? `<span class="sh-price-strike">${SH.fmtPrice(p.price)}</span>` : ""}
        </div>
        <div class="d-flex align-items-center justify-content-between">
          <div>${colorDots}</div>
          ${p.rating > 0 ? `<span class="sh-rating-pill">★ ${p.rating}</span>` : `<span class="text-muted small">No ratings yet</span>`}
        </div>
      </div>
    </div>
  </div>`;
}

function shColorToHex(name) {
  const map = {
    "Black": "#1A1A1A", "White": "#F5F5F5", "Navy": "#1B2A4A", "Maroon": "#6E1B25",
    "Olive": "#6B6E1B", "Beige": "#D9C7A3", "Grey": "#8A8A8A", "Mustard": "#D9A441",
    "Rust": "#B5502F", "Sky Blue": "#7EC8E3", "Blush Pink": "#E8B4BC", "Charcoal": "#36454F",
  };
  return map[name] || "#CCCCCC";
}

function shBindWishlistButtons(root = document) {
  root.querySelectorAll(".sh-wishlist-btn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!SH.isLoggedIn()) {
        SH.toast("Please log in to save items to your wishlist.", "info");
        window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
        return;
      }
      const productId = btn.dataset.productId;
      const icon = btn.querySelector("i");
      const isActive = btn.classList.contains("active");
      try {
        if (isActive) {
          await SH.api(`/api/wishlist/${productId}`, { method: "DELETE" });
          btn.classList.remove("active");
          icon.className = "bi bi-heart";
          SH.toast("Removed from wishlist.");
        } else {
          await SH.api(`/api/wishlist/${productId}`, { method: "POST" });
          btn.classList.add("active");
          icon.className = "bi bi-heart-fill";
          SH.toast("Added to wishlist!");
        }
      } catch (err) {
        SH.toast(err.message, "error");
      }
    });
  });
}

async function shMarkWishlistedCards(root = document) {
  if (!SH.isLoggedIn()) return;
  try {
    const wishlist = await SH.api("/api/wishlist");
    const wishlistedIds = new Set(wishlist.map((w) => w.product.id));
    root.querySelectorAll(".sh-wishlist-btn").forEach((btn) => {
      const pid = parseInt(btn.dataset.productId, 10);
      if (wishlistedIds.has(pid)) {
        btn.classList.add("active");
        btn.querySelector("i").className = "bi bi-heart-fill";
      }
    });
  } catch (e) { /* silent */ }
}
