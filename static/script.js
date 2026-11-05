const CART_KEY = "velvetaura_cart";

function getCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY) || "[]"); }
  catch { return []; }
}

function saveCart(cart) {
  localStorage.setItem(CART_KEY, JSON.stringify(cart));
  updateCartCount();
}

function updateCartCount() {
  const count = getCart().reduce((sum, item) => sum + item.qty, 0);
  document.querySelectorAll(".cart-count").forEach(el => el.textContent = count);
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

function attachAddButtons() {
  document.querySelectorAll("[data-add]").forEach(button => {
    if (button.dataset.bound) return;
    button.dataset.bound = "true";
    button.addEventListener("click", () => {
      const cart = getCart();
      const name = button.dataset.add;
      const price = Number(button.dataset.price);
      const existing = cart.find(item => item.name === name);
      if (existing) existing.qty += 1;
      else cart.push({ name, price, qty: 1 });
      saveCart(cart);
      const label = button.textContent;
      button.textContent = "Added ✓";
      setTimeout(() => button.textContent = label, 1000);
    });
  });
}

async function loadProducts() {
  const grid = document.querySelector("#product-grid");
  if (!grid) return;
  try {
    const response = await fetch("/api/products");
    if (!response.ok) return;
    const products = await response.json();
    grid.innerHTML = products.map(product => `
      <article class="product-card">
        <img src="${escapeHTML(product.image)}" alt="${escapeHTML(product.name)}">
        <span class="product-tag">${escapeHTML(product.category)}</span>
        <h3>${escapeHTML(product.name)}</h3>
        <p>${escapeHTML(product.description)}</p>
        <div class="product-bottom"><b>₹${Number(product.price)}</b>
          <button class="add-button" data-add="${escapeHTML(product.name)}" data-price="${Number(product.price)}">Add +</button>
        </div>
      </article>`).join("");
    attachAddButtons();
  } catch (error) {
    console.info("Catalog API not available; showing the products already in the page.", error);
  }
}

async function handleAuthForm(form) {
  const notice = form.querySelector(".notice");
  const submit = form.querySelector('[type="submit"]');
  const payload = {
    email: form.querySelector('[type="email"]').value,
    password: form.querySelector('[type="password"]').value
  };
  const mode = form.dataset.mode || "login";
  submit.disabled = true;
  notice.textContent = "Connecting…";
  try {
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not sign in.");
    notice.textContent = result.message;
    form.reset();
  } catch (error) {
    notice.textContent = error.message === "Failed to fetch"
      ? "Cannot reach the backend. Start the Flask server and open this site at http://127.0.0.1:5000."
      : error.message;
  } finally {
    submit.disabled = false;
  }
}

async function handleContactForm(form) {
  const notice = form.querySelector(".notice");
  const payload = Object.fromEntries(new FormData(form).entries());
  const submit = form.querySelector('[type="submit"]');
  submit.disabled = true;
  notice.textContent = "Sending…";
  try {
    const response = await fetch("/api/contact", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Could not send your enquiry.");
    notice.textContent = result.message;
    form.reset();
  } catch (error) {
    notice.textContent = error.message === "Failed to fetch"
      ? "Cannot reach the backend. Start the Flask server and open this site at http://127.0.0.1:5000."
      : error.message;
  } finally {
    submit.disabled = false;
  }
}

function renderCart() {
  const target = document.querySelector("#cart-items");
  if (!target) return;
  const cart = getCart();
  if (!cart.length) {
    target.innerHTML = '<div class="empty">Your beauty bag is waiting for something lovely.<br><br><a class="button" href="products.html" target="_blank">Explore products →</a></div>';
    return;
  }

  const total = cart.reduce((sum, item) => sum + item.price * item.qty, 0);
  target.innerHTML = cart.map((item, index) => `
    <div class="cart-row">
      <div><b>${escapeHTML(item.name)}</b><div>₹${Number(item.price)} × ${Number(item.qty)}</div></div>
      <div><b>₹${Number(item.price) * Number(item.qty)}</b> &nbsp; <button data-remove="${index}">Remove</button></div>
    </div>`).join("") + `
    <div class="cart-row"><b>Estimated total</b><b>₹${total}</b></div>
    <form class="form-wrap checkout-form" id="checkout-form">
      <h2>Delivery details</h2>
      <label for="order-name">Your name</label><input id="order-name" name="name" required>
      <label for="order-email">Email address</label><input id="order-email" name="email" type="email" required>
      <label for="order-phone">Phone number</label><input id="order-phone" name="phone" type="tel" required>
      <label for="order-address">Delivery address</label><textarea id="order-address" name="address" required></textarea>
      <button class="button" type="submit">Place order · ₹${total}</button>
      <div class="notice" aria-live="polite"></div>
    </form>`;

  target.querySelectorAll("[data-remove]").forEach(button => button.addEventListener("click", () => {
    const updated = getCart();
    updated.splice(Number(button.dataset.remove), 1);
    saveCart(updated);
    renderCart();
  }));

  target.querySelector("#checkout-form").addEventListener("submit", async event => {
    event.preventDefault();
    const form = event.currentTarget;
    const notice = form.querySelector(".notice");
    const submit = form.querySelector('[type="submit"]');
    const values = Object.fromEntries(new FormData(form).entries());
    submit.disabled = true;
    notice.textContent = "Placing your order…";
    try {
      const response = await fetch("/api/orders", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer: values, items: getCart() })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Could not place your order.");
      localStorage.removeItem(CART_KEY);
      updateCartCount();
      target.innerHTML = `<div class="empty">${escapeHTML(result.message)} Your order number is <b>#${Number(result.order_id)}</b>.<br><br>Total: <b>₹${Number(result.total)}</b></div>`;
    } catch (error) {
      notice.textContent = error.message === "Failed to fetch"
        ? "Cannot reach the backend. Start Flask and open the site at http://127.0.0.1:5000."
        : error.message;
      submit.disabled = false;
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  updateCartCount();
  attachAddButtons();
  loadProducts();
  renderCart();

  const authForm = document.querySelector('form[data-form="login"]');
  if (authForm) {
    const toggle = document.querySelector("#auth-toggle");
    toggle?.addEventListener("click", () => {
      const registering = authForm.dataset.mode !== "register";
      authForm.dataset.mode = registering ? "register" : "login";
      authForm.querySelector('[type="submit"]').textContent = registering ? "Create account →" : "Log in →";
      toggle.textContent = registering ? "Already have an account? Log in" : "Need an account? Create one";
      authForm.querySelector(".notice").textContent = registering ? "Use a password with at least 8 characters." : "";
    });
    authForm.addEventListener("submit", event => {
      event.preventDefault();
      handleAuthForm(authForm);
    });
  }

  document.querySelectorAll('form[data-form="contact"]').forEach(form => {
    form.addEventListener("submit", event => {
      event.preventDefault();
      handleContactForm(form);
    });
  });
});
