/* =========================================================
   StyleHub - Core frontend helpers
   Handles: JWT storage, authenticated fetch wrapper, toasts,
   cart badge sync, and small shared UI utilities.
   ========================================================= */

const SH = {
  TOKEN_KEY: "stylehub_token",
  USER_KEY: "stylehub_user",

  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },
  setSession(token, user) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  },
  getUser() {
    const raw = localStorage.getItem(this.USER_KEY);
    return raw ? JSON.parse(raw) : null;
  },
  isLoggedIn() {
    return !!this.getToken();
  },
  logout() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    window.location.href = "/login";
  },

  async api(path, options = {}) {
    const headers = options.headers || {};
    if (!(options.body instanceof URLSearchParams)) {
      headers["Content-Type"] = "application/json";
    }
    const token = this.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(path, { ...options, headers });

    if (res.status === 401) {
      // token invalid/expired
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.USER_KEY);
    }

    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }

    if (!res.ok) {
      const message = (data && data.detail) ? data.detail : `Request failed (${res.status})`;
      throw new Error(typeof message === "string" ? message : JSON.stringify(message));
    }
    return data;
  },

  fmtPrice(value) {
    return "₹" + Number(value).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  },

  toast(message, type = "success") {
    let container = document.querySelector(".sh-toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "sh-toast-container";
      document.body.appendChild(container);
    }
    const icon = type === "success" ? "✅" : type === "error" ? "⚠️" : "ℹ️";
    const bg = type === "success" ? "#16A085" : type === "error" ? "#C0392B" : "#2980B9";
    const el = document.createElement("div");
    el.style.cssText = `background:${bg};color:#fff;padding:12px 18px;border-radius:8px;margin-top:8px;
      box-shadow:0 6px 18px rgba(0,0,0,0.18);font-weight:600;min-width:240px;max-width:340px;
      animation:sh-fade-in .2s ease;`;
    el.innerHTML = `${icon} ${message}`;
    container.appendChild(el);
    setTimeout(() => {
      el.style.transition = "opacity .3s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 300);
    }, 2600);
  },

  async refreshCartBadge() {
    const badgeEls = document.querySelectorAll(".sh-cart-badge");
    if (!this.isLoggedIn()) {
      badgeEls.forEach((b) => (b.style.display = "none"));
      return;
    }
    try {
      const cart = await this.api("/api/cart");
      badgeEls.forEach((b) => {
        if (cart.total_items > 0) {
          b.textContent = cart.total_items;
          b.style.display = "inline-block";
        } else {
          b.style.display = "none";
        }
      });
    } catch (e) {
      /* silent fail on badge refresh */
    }
  },

  starString(rating) {
    const full = Math.round(rating);
    let out = "";
    for (let i = 0; i < 5; i++) out += i < full ? "★" : "☆";
    return out;
  },

  requireAuthOrRedirect(nextPath) {
    if (!this.isLoggedIn()) {
      window.location.href = `/login?next=${encodeURIComponent(nextPath || window.location.pathname)}`;
      return false;
    }
    return true;
  },

  requireAdminOrRedirect() {
    if (!this.isLoggedIn()) {
      window.location.href = "/login";
      return false;
    }
    const user = this.getUser();
    if (!user || !user.is_admin) {
      window.location.href = "/";
      return false;
    }
    return true;
  },

  qs(name) {
    return new URLSearchParams(window.location.search).get(name);
  },

  escapeHtml(str) {
    if (!str) return "";
    return str.replace(/[&<>"']/g, (m) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[m]));
  },
};

document.addEventListener("DOMContentLoaded", async () => {
  // Always re-verify against the server so a stale/cached localStorage
  // user object can never show the wrong role after a permissions change.
  if (SH.isLoggedIn()) {
    try {
      const freshUser = await SH.api("/api/auth/me");
      localStorage.setItem(SH.USER_KEY, JSON.stringify(freshUser));
    } catch (e) {
      /* if this fails (expired token etc.), fall through with cached data */
    }
  }

  renderAuthArea();
  SH.refreshCartBadge();

  // Global search form
  const searchForm = document.getElementById("sh-search-form");
  if (searchForm) {
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = document.getElementById("sh-search-input").value.trim();
      window.location.href = `/products${q ? "?search=" + encodeURIComponent(q) : ""}`;
    });
  }
});

function renderAuthArea() {
  const authArea = document.getElementById("sh-auth-area");
  const adminBanner = document.getElementById("sh-admin-banner");
  const adminNavSlot = document.getElementById("sh-admin-nav-slot");
  const user = SH.getUser();
  const isAdmin = !!(user && user.is_admin);

  if (adminBanner) adminBanner.style.display = isAdmin ? "block" : "none";
  if (adminNavSlot) {
    adminNavSlot.innerHTML = isAdmin
      ? `<a href="/admin" class="btn btn-sm me-2" style="background:var(--sh-accent);color:var(--sh-primary);font-weight:700;">
           <i class="bi bi-speedometer2"></i> Admin Panel
         </a>`
      : "";
  }

  if (authArea) {
    if (isAdmin) {
      authArea.innerHTML = `
        <div class="dropdown">
          <a class="nav-link dropdown-toggle d-flex align-items-center gap-1" href="#" role="button" data-bs-toggle="dropdown">
            <span class="sh-admin-pill">ADMIN</span> ${SH.escapeHtml(user.first_name || user.username)}
          </a>
          <ul class="dropdown-menu dropdown-menu-end">
            <li><h6 class="dropdown-header">Store Management</h6></li>
            <li><a class="dropdown-item" href="/admin"><i class="bi bi-speedometer2 me-1"></i> Admin Dashboard</a></li>
            <li><a class="dropdown-item" href="/admin/products"><i class="bi bi-box-seam me-1"></i> Manage Products</a></li>
            <li><a class="dropdown-item" href="/admin/orders"><i class="bi bi-receipt me-1"></i> Manage Orders</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item" href="/profile">My Profile</a></li>
            <li><a class="dropdown-item text-danger" href="#" id="sh-logout-link">Logout</a></li>
          </ul>
        </div>`;
    } else if (user) {
      authArea.innerHTML = `
        <div class="dropdown">
          <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
            👤 ${SH.escapeHtml(user.first_name || user.username)}
          </a>
          <ul class="dropdown-menu dropdown-menu-end">
            <li><a class="dropdown-item" href="/profile">My Profile</a></li>
            <li><a class="dropdown-item" href="/orders">My Orders</a></li>
            <li><a class="dropdown-item" href="/wishlist">My Wishlist</a></li>
            <li><hr class="dropdown-divider"></li>
            <li><a class="dropdown-item text-danger" href="#" id="sh-logout-link">Logout</a></li>
          </ul>
        </div>`;
    } else {
      authArea.innerHTML = `<a class="nav-link" href="/login">Login</a><a class="nav-link" href="/register">Sign Up</a>`;
    }

    const logoutLink = document.getElementById("sh-logout-link");
    if (logoutLink) {
      logoutLink.addEventListener("click", (e) => {
        e.preventDefault();
        SH.logout();
      });
    }
  }
}
