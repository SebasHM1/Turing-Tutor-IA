// static/js/ui.js
document.addEventListener('DOMContentLoaded', () => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // 1) Enlaces de UI
    const backBtn = document.querySelector('.js-back')
    const logoutBtn = document.querySelector('.js-logout')
    const logoutFrm = document.getElementById('logout-form')
    const topbar = document.querySelector('.topbar')
    const bell = document.querySelector('.bell')

    if (backBtn) backBtn.addEventListener('click', () => history.back())
    if (logoutBtn && logoutFrm) logoutBtn.addEventListener('click', () => logoutFrm.submit())

    // 2) Sombra en topbar al hacer scroll
    const setTopbarShadow = () => {
        if (!topbar) return
        const y = window.scrollY || document.documentElement.scrollTop
        topbar.classList.toggle('scrolled', y > 8)
    }
    setTopbarShadow()
    window.addEventListener('scroll', setTopbarShadow, { passive: true })

    // 3) Animaciones base
    const fadeInUp = (el, delay = 0) => {
        if (prefersReduced) return
        el.style.opacity = '0'
        el.style.transform = 'translateY(8px)'
        el.style.transition = `opacity .32s ease ${delay}ms, transform .32s ease ${delay}ms`
        requestAnimationFrame(() => {
            el.style.opacity = '1'
            el.style.transform = 'translateY(0)'
        })
    }

    // 4) Entrada inicial
    const header = document.querySelector('.welcome')
    if (header) fadeInUp(header, 0)

    // 5) Revelado por scroll con escalonado
    const revealEls = [
        ...document.querySelectorAll('.kpi'),
        ...document.querySelectorAll('.course-card'),
        ...document.querySelectorAll('.join-card')
    ]
    if (!prefersReduced) {
        const io = new IntersectionObserver(entries => {
            entries.forEach(e => {
                if (e.isIntersecting) {
                    const index = revealEls.indexOf(e.target)
                    const delay = Math.max(0, index) * 60
                    fadeInUp(e.target, delay)
                    io.unobserve(e.target)
                }
            })
        }, { threshold: 0.08 })
        revealEls.forEach(el => io.observe(el))
    }

    // 6) Contador animado para KPIs
    const animateNumber = (el, to, dur = 800) => {
        if (prefersReduced) { el.textContent = to; return }
        const start = performance.now()
        const from = 0
        const isPercent = String(el.dataset.type || '').toLowerCase() === 'percent'
        const target = Number(to)
        const fmt = v => isPercent ? `${Math.round(v)}%` : `${Math.round(v)}`
        const tick = now => {
            const t = Math.min(1, (now - start) / dur)
            const eased = 1 - Math.pow(1 - t, 3)
            el.textContent = fmt(from + (target - from) * eased)
            if (t < 1) requestAnimationFrame(tick)
        }
        requestAnimationFrame(tick)
    }

    // Busca los valores de kpi y los anima si están en números
    document.querySelectorAll('.kpi .value').forEach(v => {
        const raw = v.textContent.trim()
        const isPercent = raw.endsWith('%')
        const num = parseInt(raw.replace('%', ''), 10)
        if (!Number.isNaN(num)) {
            if (isPercent) v.dataset.type = 'percent'
            animateNumber(v, num)
        }
    })

    // 7) Ripple mejorado en todos los botones e icon buttons
    const addRipple = el => {
        el.addEventListener('click', ev => {
            const rect = el.getBoundingClientRect()
            const ripple = document.createElement('span')
            ripple.className = 'ripple'
            const size = Math.max(rect.width, rect.height)
            ripple.style.width = ripple.style.height = size + 'px'
            ripple.style.left = ev.clientX - rect.left - size / 2 + 'px'
            ripple.style.top = ev.clientY - rect.top - size / 2 + 'px'
            el.appendChild(ripple)
            ripple.addEventListener('animationend', () => ripple.remove())
        }, { passive: true })
    }
    document.querySelectorAll('.btn, .icon-button, .btn-back').forEach(addRipple)

    // 8) Micro animación de la campana al hacer clic
    if (bell && !prefersReduced) {
        bell.addEventListener('click', () => {
            bell.animate(
                [
                    { transform: 'rotate(0)' },
                    { transform: 'rotate(-12deg)' },
                    { transform: 'rotate(10deg)' },
                    { transform: 'rotate(-6deg)' },
                    { transform: 'rotate(0)' }
                ],
                { duration: 450, easing: 'ease-out' }
            )
        })
    }

    // 9) Foco elegante en la búsqueda
    const searchInput = document.querySelector('.search input')
    if (searchInput) {
        searchInput.addEventListener('focus', () => searchInput.classList.add('is-focused'))
        searchInput.addEventListener('blur', () => searchInput.classList.remove('is-focused'))
    }
})
