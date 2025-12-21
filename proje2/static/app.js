/**
 * ===============================================================================
 * Üniversite Sınav Programı Hazırlama Sistemi - JavaScript Dosyası
 * Bu dosya tüm interaktif özellikler ve kullanıcı deneyimi iyileştirmelerini içerir.
 * Özellikler: Animasyonlar, form iyileştirmeleri, sticky navigation, tablo etkileşimleri
 * ===============================================================================
 */

// Sayfa yüklendiğinde tüm interaktif özellikleri başlat
document.addEventListener('DOMContentLoaded', function() {
    // Tüm interaktif özellikleri sırayla başlat
    initAnimations();           // Giriş animasyonları
    initFormEnhancements();     // Form iyileştirmeleri
    initTableEnhancements();    // Tablo etkileşimleri
    initNavigationEnhancements(); // Navigasyon iyileştirmeleri
    initStickyNavigation();     // Sticky (yapışkan) navigasyon
});

/**
 * Giriş animasyonlarını başlat
 * Kartlar ve hero section elementleri için fade-in efektleri
 */
function initAnimations() {
    // Kartlara kademeli fade-in animasyonu ekle
    const cards = document.querySelectorAll('.card-like');
    cards.forEach((card, index) => {
        card.style.opacity = '0'; // Başlangıçta görünmez
        card.style.transform = 'translateY(20px)'; // Aşağıdan yukarı hareket
        card.style.transition = 'all 0.6s ease'; // Yumuşak geçiş
        
        // Her kart için farklı gecikme süresi
        setTimeout(() => {
            card.style.opacity = '1'; // Görünür yap
            card.style.transform = 'translateY(0)'; // Yerine getir
        }, index * 100); // 100ms aralıklarla
    });

    // Hero section elementleri için animasyon
    const heroElements = document.querySelectorAll('.hero-content > *');
    heroElements.forEach((element, index) => {
        element.style.opacity = '0'; // Başlangıçta görünmez
        element.style.transform = 'translateY(30px)'; // Daha fazla hareket
        element.style.transition = 'all 0.8s ease'; // Daha uzun geçiş
        
        // Daha uzun gecikme süreleri
        setTimeout(() => {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, (index + 1) * 200); // 200ms aralıklarla
    });
}

/**
 * Form iyileştirmelerini başlat
 * Floating label efektleri, validation ve buton etkileşimleri
 */
function initFormEnhancements() {
    // Floating label efekti ekle
    const formControls = document.querySelectorAll('.form-control');
    formControls.forEach(input => {
        // Focus/blur efektleri ekle
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });

        // Gerçek zamanlı validation geri bildirimi
        input.addEventListener('input', function() {
            if (this.hasAttribute('required')) {
                if (this.value.trim()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                }
            }
        });
    });

    // Gelişmiş buton etkileşimleri
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Ripple efekti
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

/**
 * Tablo etkileşimlerini iyileştir
 * Hover efektleri ve sıralama göstergeleri
 */
function initTableEnhancements() {
    const tableRows = document.querySelectorAll('tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.02)';
            this.style.boxShadow = '0 4px 15px rgba(22, 160, 133, 0.15)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
            this.style.boxShadow = 'none';
        });
    });

    // Sıralama göstergeleri ekle (sadece görsel)
    const tableHeaders = document.querySelectorAll('th');
    tableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            // Sıralama için görsel geri bildirim
            tableHeaders.forEach(h => h.classList.remove('sorted'));
            this.classList.add('sorted');
        });
    });
}

/**
 * Navigasyon iyileştirmelerini başlat
 * Navbar animasyonları ve aktif sayfa gösterimi
 */
function initNavigationEnhancements() {
    // Yumuşak navbar collapse animasyonu
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            this.classList.toggle('active');
        });
    }

    // Mevcut sayfaya aktif durum ekle
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
            link.style.backgroundColor = 'var(--light-gray)';
            link.style.color = 'var(--primary-green)';
        }
    });
}

/**
 * Utility function for smooth scrolling
 */
function smoothScrollTo(element) {
    element.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
    });
}

/**
 * Show loading state for forms
 */
function showLoadingState(form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '⏳ İşleniyor...';
        submitBtn.disabled = true;
        
        // Reset after 3 seconds (fallback)
        setTimeout(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }, 3000);
    }
}

/**
 * Add loading states to forms
 */
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function() {
        showLoadingState(this);
    });
});

/**
 * Add CSS for ripple effect
 */
const style = document.createElement('style');
style.textContent = `
    .btn {
        position: relative;
        overflow: hidden;
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .focused .form-label {
        color: var(--primary-green);
        font-weight: 600;
    }
    
    .navbar-toggler.active {
        transform: rotate(90deg);
    }
    
    th.sorted {
        background-color: var(--primary-green) !important;
        color: white !important;
    }
    
    th.sorted::after {
        content: ' ↕️';
    }
    
    .is-valid {
        border-color: var(--accent-green) !important;
        box-shadow: 0 0 0 0.2rem rgba(46, 204, 113, 0.25) !important;
    }
    
    .is-invalid {
        border-color: #e74c3c !important;
        box-shadow: 0 0 0 0.2rem rgba(231, 76, 60, 0.25) !important;
    }
`;
document.head.appendChild(style);

/**
 * Add keyboard shortcuts
 */
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + K for search (if search exists)
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('input[type="search"], input[name="faculty"], input[name="department"]');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close modals or clear focus
    if (e.key === 'Escape') {
        document.activeElement.blur();
    }
});

/**
 * Add print styles optimization
 */
window.addEventListener('beforeprint', function() {
    document.body.classList.add('printing');
});

window.addEventListener('afterprint', function() {
    document.body.classList.remove('printing');
});/
**
 * Initialize sticky navigation functionality
 */
function initStickyNavigation() {
    const stickyNav = document.getElementById('stickyNav');
    const stickyHamburger = document.getElementById('stickyHamburger');
    const stickyMenu = document.getElementById('stickyMenu');
    const stickyOverlay = document.getElementById('stickyOverlay');
    const mainNavbar = document.getElementById('mainNavbar');
    
    if (!stickyNav || !stickyHamburger || !stickyMenu || !stickyOverlay || !mainNavbar) {
        return;
    }

    let lastScrollTop = 0;
    let isMenuOpen = false;
    let navbarHeight = mainNavbar.offsetHeight;

    // Show/hide sticky nav based on scroll
    function handleScroll() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Show sticky nav when scrolled past main navbar
        if (scrollTop > navbarHeight + 50) {
            if (!stickyNav.classList.contains('visible')) {
                stickyNav.classList.add('visible');
                document.body.classList.add('sticky-nav-visible');
            }
        } else {
            if (stickyNav.classList.contains('visible')) {
                stickyNav.classList.remove('visible');
                document.body.classList.remove('sticky-nav-visible');
                closeStickyMenu(); // Close menu when hiding nav
            }
        }
        
        lastScrollTop = scrollTop;
    }

    // Open sticky menu
    function openStickyMenu() {
        isMenuOpen = true;
        stickyMenu.classList.add('open');
        stickyOverlay.classList.add('active');
        stickyHamburger.classList.add('active');
        document.body.classList.add('sticky-menu-open');
        
        // Add entrance animation to menu items
        const menuItems = stickyMenu.querySelectorAll('.sticky-menu-item');
        menuItems.forEach((item, index) => {
            item.style.opacity = '0';
            item.style.transform = 'translateX(20px)';
            setTimeout(() => {
                item.style.transition = 'all 0.3s ease';
                item.style.opacity = '1';
                item.style.transform = 'translateX(0)';
            }, index * 50);
        });
    }

    // Close sticky menu
    function closeStickyMenu() {
        isMenuOpen = false;
        stickyMenu.classList.remove('open');
        stickyOverlay.classList.remove('active');
        stickyHamburger.classList.remove('active');
        document.body.classList.remove('sticky-menu-open');
    }
    
    // Make closeStickyMenu available globally for swipe gestures
    window.closeStickyMenu = closeStickyMenu;

    // Toggle sticky menu
    function toggleStickyMenu() {
        if (isMenuOpen) {
            closeStickyMenu();
        } else {
            openStickyMenu();
        }
    }

    // Event listeners
    window.addEventListener('scroll', throttle(handleScroll, 10));
    stickyHamburger.addEventListener('click', toggleStickyMenu);
    stickyOverlay.addEventListener('click', closeStickyMenu);

    // Close menu when clicking on menu items (for navigation)
    const menuItems = stickyMenu.querySelectorAll('.sticky-menu-item');
    menuItems.forEach(item => {
        item.addEventListener('click', () => {
            // Add a small delay to allow navigation to start
            setTimeout(closeStickyMenu, 100);
        });
    });

    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && isMenuOpen) {
            closeStickyMenu();
        }
    });

    // Handle window resize
    window.addEventListener('resize', function() {
        navbarHeight = mainNavbar.offsetHeight;
        if (window.innerWidth > 768 && isMenuOpen) {
            closeStickyMenu();
        }
    });

    // Set active menu item based on current page
    function setActiveMenuItem() {
        const currentPath = window.location.pathname;
        const menuItems = stickyMenu.querySelectorAll('.sticky-menu-item');
        
        menuItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('href') === currentPath) {
                item.classList.add('active');
            }
        });
    }

    // Initialize active menu item
    setActiveMenuItem();

    // Add smooth scroll behavior for anchor links in sticky menu
    const anchorLinks = stickyMenu.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                closeStickyMenu();
                setTimeout(() => {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }, 300);
            }
        });
    });
}

/**
 * Throttle function for performance optimization
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

/**
 * Add swipe gesture support for mobile menu
 */
function initSwipeGestures() {
    let startX = 0;
    let startY = 0;
    let endX = 0;
    let endY = 0;

    document.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
    });

    document.addEventListener('touchend', function(e) {
        endX = e.changedTouches[0].clientX;
        endY = e.changedTouches[0].clientY;
        handleSwipe();
    });

    function handleSwipe() {
        const deltaX = endX - startX;
        const deltaY = endY - startY;
        const minSwipeDistance = 50;

        // Swipe left to close menu
        if (deltaX < -minSwipeDistance && Math.abs(deltaY) < 100) {
            const stickyMenu = document.getElementById('stickyMenu');
            if (stickyMenu && stickyMenu.classList.contains('open')) {
                closeStickyMenu();
            }
        }
    }
}

// Initialize swipe gestures
document.addEventListener('DOMContentLoaded', initSwipeGestures);