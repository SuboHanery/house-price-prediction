/* script.js — HousePrice AI Predictor */
'use strict';

// ─── House thumbnail images (randomly assigned to Similar Properties) ─────────
const HOUSE_IMAGES = [
    '/static/images/house1.png',
    '/static/images/house2.png',
    '/static/images/house3.png',
    '/static/images/house4.png',
    '/static/images/house5.png',
];

function randomHouseImg(seed) {
    // Use seed (index) so the same prediction always gives same images
    return HOUSE_IMAGES[seed % HOUSE_IMAGES.length];
}

// ─── Sidebar Toggle (desktop collapse + mobile overlay) ───────────────────────
function toggleSidebar() {
    const sidebar  = document.getElementById('sidebar');
    const main     = document.getElementById('mainContent');
    const backdrop = document.getElementById('sidebarBackdrop');
    const isMobile = window.innerWidth <= 700;

    if (isMobile) {
        // Mobile: slide-in overlay
        const isOpen = sidebar.classList.contains('mobile-open');
        if (isOpen) {
            closeSidebar();
        } else {
            sidebar.classList.add('mobile-open');
            backdrop.classList.add('active');
            document.body.style.overflow = 'hidden'; // prevent scroll behind
        }
    } else {
        // Desktop: collapse/expand
        const collapsed = sidebar.classList.toggle('collapsed');
        main.style.marginLeft = collapsed ? '0' : 'var(--sidebar-w)';
    }
}

function closeSidebar() {
    const sidebar  = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    sidebar.classList.remove('mobile-open');
    backdrop.classList.remove('active');
    document.body.style.overflow = '';
}

// Close sidebar on resize if switching to desktop
window.addEventListener('resize', () => {
    if (window.innerWidth > 700) {
        closeSidebar();
        document.body.style.overflow = '';
    }
});

function toggleTheme() {
    const html  = document.documentElement;
    const moon  = document.getElementById('moonIcon');
    const sun   = document.getElementById('sunIcon');
    const isDark = html.getAttribute('data-theme') === 'dark';

    if (isDark) {
        html.setAttribute('data-theme', 'light');
        moon.style.display = '';
        sun.style.display  = 'none';
        localStorage.setItem('theme', 'light');
    } else {
        html.setAttribute('data-theme', 'dark');
        moon.style.display = 'none';
        sun.style.display  = '';
        localStorage.setItem('theme', 'dark');
    }
}

// ─── Sidebar Toggle ───────────────────────────────────────────────────────────
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const main    = document.getElementById('mainContent');
    const isCollapsed = sidebar.style.transform === 'translateX(-100%)';

    if (isCollapsed) {
        sidebar.style.transform = '';
        main.style.marginLeft   = '';
    } else {
        sidebar.style.transform = 'translateX(-100%)';
        main.style.marginLeft   = '0';
    }
}

// ─── Restore theme on load ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        const moon = document.getElementById('moonIcon');
        const sun  = document.getElementById('sunIcon');
        if (moon) moon.style.display = 'none';
        if (sun)  sun.style.display  = '';
    }

    // Animate feature bars on Insights page
    animateBars();

    // Attach predict form handler
    const form = document.getElementById('predictForm');
    if (form) {
        form.addEventListener('submit', handlePredict);
    }
});

// ─── Animate Feature Importance Bars ─────────────────────────────────────────
function animateBars() {
    const bars = document.querySelectorAll('.bar-fill');
    if (bars.length === 0) return;

    const stored = {};
    bars.forEach(bar => {
        stored[bar] = bar.style.width;
        bar.style.width = '0';
    });

    setTimeout(() => {
        bars.forEach(bar => {
            bar.style.width = stored[bar];
        });
    }, 200);
}

// ─── Predict Form Handler (AJAX) ──────────────────────────────────────────────
function handlePredict(e) {
    e.preventDefault();

    const form   = document.getElementById('predictForm');
    const btn    = document.getElementById('predictBtn');
    const errors = validatePredictForm();

    if (errors.length > 0) {
        showFormError(errors[0]);
        return;
    }

    // Build payload
    const payload = {
        location:         document.getElementById('location').value,
        area_sqft:        document.getElementById('area_sqft').value,
        bedrooms:         document.getElementById('bedrooms').value,
        bathrooms:        document.getElementById('bathrooms').value,
        parking:          document.getElementById('parking').value,
        has_gym:          document.getElementById('has_gym').checked ? 1 : 0,
        has_swimming_pool:document.getElementById('has_swimming_pool').checked ? 1 : 0,
        has_ground:       document.getElementById('has_ground').checked ? 1 : 0,
    };

    // Loading state
    btn.disabled    = true;
    btn.textContent = '⏳ Calculating...';
    setResultLoading(true);

    fetch('/api/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            showFormError(data.error);
            setResultLoading(false);
        } else {
            displayResult(data);
        }
    })
    .catch(err => {
        showFormError('Network error. Please ensure the server is running.');
        setResultLoading(false);
        console.error(err);
    })
    .finally(() => {
        btn.disabled    = false;
        btn.innerHTML   = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="16" height="16"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>&nbsp;Predict Price';
    });
}

// ─── Validation ───────────────────────────────────────────────────────────────
function validatePredictForm() {
    const errors = [];
    const location = document.getElementById('location').value;
    const area     = document.getElementById('area_sqft').value;
    const bedrooms = document.getElementById('bedrooms').value;
    const bathrooms= document.getElementById('bathrooms').value;

    if (!location) errors.push('Please select a location in Bangalore.');
    if (!area || parseFloat(area) < 100) errors.push('Please enter a valid built-up area (min 100 sq ft).');
    if (!bedrooms) errors.push('Please select number of bedrooms.');
    if (!bathrooms) errors.push('Please select number of bathrooms.');

    return errors;
}

// ─── Loading state for result panel ──────────────────────────────────────────
function setResultLoading(loading) {
    const priceNum = document.getElementById('priceNum');
    const sqft     = document.getElementById('resultSqft');
    const range    = document.getElementById('resultRange');
    const conf     = document.getElementById('resultConfidence');
    const compared = document.getElementById('resultCompared');

    if (loading) {
        if (priceNum) priceNum.textContent = '···';
        if (sqft)     sqft.textContent     = '(calculating...)';
        if (range)    range.textContent    = '···';
        if (conf)     conf.textContent     = '···';
        if (compared) compared.textContent = '···';
    }
}

// ─── Format price: Lakhs below 100, Crores at or above ───────────────────────
function formatPrice(lakhs) {
    if (lakhs >= 100) {
        return (lakhs / 100).toFixed(2) + ' Cr';
    }
    return lakhs.toFixed(2) + 'L';
}

function formatPriceRange(low, high) {
    if (low >= 100 || high >= 100) {
        return `₹${(low / 100).toFixed(2)} Cr – ₹${(high / 100).toFixed(2)} Cr`;
    }
    return `₹${low.toFixed(1)}L – ₹${high.toFixed(1)}L`;
}

// ─── Display Prediction Result ────────────────────────────────────────────────
function displayResult(data) {
    const price = data.price;   // in Lakhs
    const isCr  = price >= 100;

    // Animated price counter
    const priceNum = document.getElementById('priceNum');
    if (priceNum) {
        if (isCr) {
            animateNumber(priceNum, 0, price / 100, 900, val => val.toFixed(2) + ' Cr');
        } else {
            animateNumber(priceNum, 0, price, 900, val => val.toFixed(2) + 'L');
        }
    }

    // Per sqft line
    const sqft = document.getElementById('resultSqft');
    if (sqft) sqft.textContent = `(${data.per_sqft} per sq ft)`;

    // Price range — also convert if needed
    const range = document.getElementById('resultRange');
    if (range) range.textContent = isCr ? data.price_range_cr : data.price_range;

    const conf = document.getElementById('resultConfidence');
    if (conf) conf.textContent = data.confidence;

    const compared = document.getElementById('resultCompared');
    if (compared) compared.textContent = data.similar ? data.similar.length + ' found' : '--';

    // Similar properties
    const simList = document.getElementById('similarList');
    if (simList) {
        if (data.similar && data.similar.length > 0) {
            simList.innerHTML = data.similar.map((p, idx) => {
                const imgOffset = Math.floor(Math.random() * HOUSE_IMAGES.length);
                const imgSrc    = randomHouseImg(idx + imgOffset);
                return `
                <div class="similar-item">
                    <div class="similar-img-wrap">
                        <img src="${imgSrc}" alt="Property" class="similar-img-photo"
                             onerror="this.parentElement.innerHTML='🏠'">
                    </div>
                    <div class="similar-info">
                        <p class="similar-title">${p.title}</p>
                        <p class="similar-location">${p.location}, Bangalore &nbsp;·&nbsp; ${p.area}</p>
                    </div>
                    <span class="similar-price">${p.price_formatted}</span>
                </div>`;
            }).join('');
        } else {
            simList.innerHTML = '<p style="font-size:0.82rem;color:var(--text-muted);padding:10px 0;text-align:center;">No similar properties found</p>';
        }
    }
}

// ─── Number Animation ─────────────────────────────────────────────────────────
function animateNumber(el, from, to, duration, formatter) {
    const start = performance.now();
    function step(now) {
        const elapsed  = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased    = 1 - Math.pow(1 - progress, 3);
        const current  = from + (to - from) * eased;
        el.textContent = formatter(current);
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ─── Error Display ────────────────────────────────────────────────────────────
function showFormError(msg) {
    // Remove any existing error
    const existing = document.getElementById('formError');
    if (existing) existing.remove();

    const err = document.createElement('div');
    err.id = 'formError';
    err.style.cssText = `
        background:#fce8e6; border:1px solid #ea4335; border-radius:6px;
        color:#c5221f; font-size:0.83rem; font-weight:500;
        padding:10px 14px; margin-top:10px;
    `;
    err.textContent = '⚠ ' + msg;

    const form = document.getElementById('predictForm');
    if (form) form.appendChild(err);
    setTimeout(() => { if (err.parentNode) err.remove(); }, 5000);
}

console.log('HousePrice AI — Ready!');

// ─── PWA: Register Service Worker ─────────────────────────────────────────────
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .then(reg => console.log('SW registered:', reg.scope))
            .catch(err => console.log('SW failed:', err));
    });
}

// ─── PWA: Show Install Banner ─────────────────────────────────────────────────
let deferredPrompt;
window.addEventListener('beforeinstallprompt', e => {
    e.preventDefault();
    deferredPrompt = e;

    // Show a subtle install banner at the top
    const banner = document.createElement('div');
    banner.id = 'installBanner';
    banner.innerHTML = `
        <div style="
            position:fixed; top:0; left:0; right:0; z-index:999;
            background:linear-gradient(135deg,#1a73e8,#0d47a1);
            color:white; padding:12px 16px;
            display:flex; align-items:center; justify-content:space-between;
            font-size:0.85rem; font-weight:500;
            box-shadow:0 2px 12px rgba(0,0,0,0.2);
        ">
            <span>🏠 Install House Price App on your phone!</span>
            <div style="display:flex;gap:8px;">
                <button id="installBtn" style="
                    background:white; color:#1a73e8; border:none;
                    padding:6px 14px; border-radius:20px;
                    font-weight:700; cursor:pointer; font-size:0.82rem;
                ">Install</button>
                <button id="dismissBanner" style="
                    background:transparent; color:rgba(255,255,255,0.8);
                    border:none; cursor:pointer; font-size:1.1rem; padding:2px 6px;
                ">✕</button>
            </div>
        </div>
    `;
    document.body.prepend(banner);

    document.getElementById('installBtn').addEventListener('click', () => {
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(choice => {
            if (choice.outcome === 'accepted') banner.remove();
            deferredPrompt = null;
        });
    });

    document.getElementById('dismissBanner').addEventListener('click', () => {
        banner.remove();
    });
});

window.addEventListener('appinstalled', () => {
    const banner = document.getElementById('installBanner');
    if (banner) banner.remove();
    console.log('PWA installed!');
});
