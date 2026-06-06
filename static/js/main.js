// ═══════════════════════════════════════════════════════
//  Pastely — main.js
//  Script utama yang berjalan di semua halaman
// ═══════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {

  // ── Hamburger menu mobile ──────────────────────────────
  const menuToggle = document.getElementById('menu-toggle');
  const mobileMenu = document.getElementById('mobile-menu');

  if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', () => {
      mobileMenu.classList.toggle('hidden');
    });
    // Tutup menu saat klik di luar
    document.addEventListener('click', (e) => {
      if (!menuToggle.contains(e.target) && !mobileMenu.contains(e.target)) {
        mobileMenu.classList.add('hidden');
      }
    });
  }

  // ── Inisialisasi highlight.js ─────────────────────────
  if (typeof hljs !== 'undefined') {
    document.querySelectorAll('pre code').forEach(el => {
      hljs.highlightElement(el);
    });
  }

  // ── Auto-dismiss flash messages setelah 5 detik ───────
  const flashMessages = document.querySelectorAll('[class^="flash-"]');
  flashMessages.forEach(msg => {
    setTimeout(() => {
      msg.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      msg.style.opacity = '0';
      msg.style.transform = 'translateY(-8px)';
      setTimeout(() => msg.remove(), 400);
    }, 5000);
  });

  // ── Konfirmasi sebelum navigasi meninggalkan form ─────
  const pasteForm = document.getElementById('paste-form');
  if (pasteForm) {
    let formDirty = false;
    const contentArea = document.getElementById('content-area');
    if (contentArea) {
      contentArea.addEventListener('input', () => { formDirty = true; });
    }
    pasteForm.addEventListener('submit', () => { formDirty = false; });
    window.addEventListener('beforeunload', (e) => {
      if (formDirty) {
        e.preventDefault();
        e.returnValue = 'Perubahan belum disimpan. Yakin mau keluar?';
      }
    });
  }

});
