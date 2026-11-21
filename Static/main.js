document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }
  const amount = document.getElementById("amount-display");
  const cents = document.getElementById("amount-cents");
  if (amount && cents) {
    const update = () => cents.value = Math.round((Number(amount.value) || 0) * 100);
    amount.addEventListener("input", update);
    update();
  }
});
