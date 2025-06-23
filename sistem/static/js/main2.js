/**
 * REKOMENDASI BUKU - MAIN JAVASCRIPT
 *
 * Kode ini diatur dalam sebuah objek utama `App` untuk menghindari polusi global scope
 * dan memisahkan logika berdasarkan fungsinya (components, utils, theme, etc.).
 *
 * @version 1.0.0
 * @date 22 Juni 2025
 */
document.addEventListener('DOMContentLoaded', () => {

    const App = {
        // Konfigurasi dan konstanta
        config: {
            icons: {
                eyeOpen: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 13c-3.03 0-5.5-2.47-5.5-5.5s2.47-5.5 5.5-5.5 5.5 2.47 5.5 5.5-2.47 5.5-5.5 5.5zm0-9c-1.93 0-3.5 1.57-3.5 3.5s1.57 3.5 3.5 3.5 3.5-1.57 3.5-3.5-1.57-3.5-3.5-3.5z"/></svg>`,
                eyeClosed: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/></svg>`
            }
        },

        // Fungsi-fungsi utilitas/pembantu
        utils: {
            /**
             * Menampilkan notifikasi sementara di layar.
             * @param {string} message - Pesan yang akan ditampilkan.
             * @param {string} type - Tipe notifikasi ('success', 'error', 'info').
             */
            showNotification(message, type = 'info') {
                document.querySelectorAll('.notification').forEach(n => n.remove());
                const notification = document.createElement('div');
                notification.className = `notification notification--${type}`;
                notification.textContent = message;
                Object.assign(notification.style, {
                    position: 'fixed', top: '20px', right: '20px', padding: '12px 24px',
                    borderRadius: '4px', color: 'white', fontWeight: '500', zIndex: '9999',
                    transform: 'translateX(120%)', transition: 'transform 0.5s ease-in-out',
                    backgroundColor: type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#6b7280'
                });
                document.body.appendChild(notification);
                setTimeout(() => { notification.style.transform = 'translateX(0)'; }, 10);
                setTimeout(() => {
                    notification.style.transform = 'translateX(120%)';
                    notification.addEventListener('transitionend', () => notification.remove());
                }, 3000);
            },
            /**
             * Mencegah fungsi dijalankan berulang kali dalam waktu singkat.
             * @param {Function} func - Fungsi yang akan di-debounce.
             * @param {number} wait - Waktu tunggu dalam milidetik.
             */
            debounce(func, wait) {
                let timeout;
                return function executedFunction(...args) {
                    const later = () => {
                        clearTimeout(timeout);
                        func(...args);
                    };
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                };
            }
        },

        // Logika untuk komponen UI
        components: {
            /**
             * Mengaktifkan tombol lihat/sembunyikan password.
             */
initPasswordToggle() {
    const toggles = document.querySelectorAll('.icon-eye');

    toggles.forEach(toggle => {
        // Mencari pembungkus terdekat dengan class .password-group
        const parent = toggle.closest('.password-group');
        if (!parent) return;

        const input = parent.querySelector('input[name="password"]');
        if (!input) return;

        toggle.addEventListener('click', function() {
            // Cek tipe input saat ini
            const isPassword = input.type === 'password';
            // Ubah tipe inputnya
            input.type = isPassword ? 'text' : 'password';

            // [PENTING] JavaScript HANYA bertugas menukar stiker/kelas CSS
            this.classList.toggle('is-visible');
        });
    });
},

            /**
             * Memberi highlight pada link navigasi yang aktif.
             * Disederhanakan untuk bekerja lebih baik dengan URL Django.
             */
            highlightActiveNav() {
                const currentPath = window.location.pathname;
                document.querySelectorAll('.nav-links a').forEach(link => {
                    link.classList.remove('active');
                    link.removeAttribute('aria-current');
                    // Mencocokkan path URL secara langsung, lebih andal untuk Django
                    if (link.getAttribute('href') === currentPath) {
                        link.classList.add('active');
                        link.setAttribute('aria-current', 'page');
                    }
                });
            },

            /**
             * Mengaktifkan smooth scroll untuk link anchor (misal: #section).
             */
            initSmoothScroll() {
                document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                    anchor.addEventListener('click', function (e) {
                        const targetElement = document.querySelector(this.getAttribute('href'));
                        if (targetElement) {
                            e.preventDefault();
                            targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }
                    });
                });
            }
        },

        // Logika untuk menangani tema (terang/gelap)
        theme: {
            init() {
                try {
                    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
                    document.documentElement.setAttribute('data-theme', savedTheme);
                } catch (e) {
                    console.warn('Gagal mengakses localStorage untuk tema.');
                }
            }
        },

        // Pengatur event listener utama
        initEventHandlers() {
            // Menangani perubahan ukuran window dengan debounce untuk performa
            const handleResize = App.utils.debounce(() => {
                App.components.highlightActiveNav();
                console.log(`Window resized to: ${window.innerWidth}px`);
            }, 250);
            window.addEventListener('resize', handleResize);
        },

        // Titik masuk utama aplikasi
        init() {
            App.theme.init();
            App.components.initPasswordToggle();
            App.components.highlightActiveNav();
            App.components.initSmoothScroll();
            App.initEventHandlers();

            console.log('Aplikasi JavaScript berhasil diinisialisasi.');
        }
    };

    // Jalankan aplikasi
    App.init();

});