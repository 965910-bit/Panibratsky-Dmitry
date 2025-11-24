// js/main.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('Сайт Панибратского Дмитрия загружен');

    // Плавная прокрутка для навигации
    const navLinks = document.querySelectorAll('a[href^="#"]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                const headerHeight = document.querySelector('.header').offsetHeight;
                const targetPosition = targetElement.offsetTop - headerHeight - 20;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Анимация появления элементов при скролле
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Применяем анимацию к карточкам экспертиз
    const expertiseCards = document.querySelectorAll('.expertise-card');
    expertiseCards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = `opacity 0.6s ease ${index * 0.2}s, transform 0.6s ease ${index * 0.2}s`;
        observer.observe(card);
    });

    // Подсветка активного пункта меню при скролле
    const sections = document.querySelectorAll('section[id]');
    
    function highlightNav() {
        const scrollY = window.pageYOffset;
        
        sections.forEach(section => {
            const sectionHeight = section.offsetHeight;
            const sectionTop = section.offsetTop - 100;
            const sectionId = section.getAttribute('id');
            
            if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) {
                const navLink = document.querySelector(`.nav-list a[href="#${sectionId}"]`);
                if (navLink) {
                    navLink.style.backgroundColor = 'rgba(255,255,255,0.2)';
                }
            } else {
                const navLink = document.querySelector(`.nav-list a[href="#${sectionId}"]`);
                if (navLink) {
                    navLink.style.backgroundColor = 'transparent';
                }
            }
        });
    }

    window.addEventListener('scroll', highlightNav);
});

// Обработка ошибок загрузки ресурсов
window.addEventListener('error', function(e) {
    console.error('Ошибка загрузки ресурса:', e);
});
