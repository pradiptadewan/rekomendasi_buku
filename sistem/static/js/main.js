// Interaksi kecil di sisi browser. Semua halaman tetap berfungsi tanpa JavaScript.
(() => {
    // Menu navigasi di layar kecil
    const navbar = document.querySelector('.navbar');
    const toggle = document.querySelector('[data-nav-toggle]');
    toggle?.addEventListener('click', () => {
        const open = navbar.classList.toggle('is-open');
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'Tutup menu' : 'Buka menu');
    });

    // Tampilkan / sembunyikan password
    document.querySelectorAll('[data-password-toggle]').forEach((button) => {
        const input = button.parentElement.querySelector('input');
        button.addEventListener('click', () => {
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            button.classList.toggle('is-visible', show);
            button.setAttribute('aria-label', show ? 'Sembunyikan password' : 'Tampilkan password');
        });
    });

    // Notifikasi otomatis hilang setelah beberapa detik
    const dismiss = (toast) => {
        toast.classList.add('is-leaving');
        setTimeout(() => toast.remove(), 200);
    };
    document.querySelectorAll('[data-toast]').forEach((toast) => {
        toast.querySelector('[data-toast-close]')?.addEventListener('click', () => dismiss(toast));
        setTimeout(() => dismiss(toast), 5000);
    });

    // Filter koleksi langsung diterapkan saat pilihan berubah
    document.querySelectorAll('form[data-autosubmit]').forEach((form) => {
        form.addEventListener('change', () => form.submit());
    });

    // Sampul yang gagal dimuat diganti dengan sampul teks
    document.querySelectorAll('img[data-cover]').forEach((img) => {
        const showFallback = () => {
            img.remove();
            img.nextElementSibling?.removeAttribute('hidden');
        };
        if (img.complete && img.naturalWidth === 0) showFallback();
        else img.addEventListener('error', showFallback, { once: true });
    });

    // Tombol "Kembali" memakai riwayat browser jika datang dari situs ini
    document.querySelectorAll('[data-history-back]').forEach((link) => {
        link.addEventListener('click', (event) => {
            if (document.referrer.startsWith(window.location.origin) && history.length > 1) {
                event.preventDefault();
                history.back();
            }
        });
    });
})();
