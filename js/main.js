// Main JavaScript functionality

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeNavigation();
    initializeActiveNav();
    initializeSmoothScrolling();
});

// Smooth scrolling for navigation links
function initializeNavigation() {
    const navLinks = document.querySelectorAll('a[href^="#"]');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Set active navigation item
function initializeActiveNav() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-links a');
    
    navLinks.forEach(link => {
        const linkHref = link.getAttribute('href');
        
        // For main page - handle section clicks
        if (currentPage === 'index.html' && linkHref.startsWith('#')) {
            link.addEventListener('click', function() {
                navLinks.forEach(l => l.classList.remove('active'));
                this.classList.add('active');
            });
        }
        
        // For other pages - mark current page as active
        if (linkHref === currentPage || (currentPage === 'index.html' && linkHref.startsWith('#'))) {
            link.classList.add('active');
        }
    });

    // Set first nav item as active on main page load
    if (currentPage === 'index.html' && navLinks.length > 0) {
        const firstNavItem = document.querySelector('.nav-links a[href^="#"]');
        if (firstNavItem && !document.querySelector('.nav-links a.active')) {
            firstNavItem.classList.add('active');
        }
    }
}

// Smooth scrolling for same-page links
function initializeSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
}

// Handle scroll to update active nav item
window.addEventListener('scroll', function() {
    if (window.location.pathname.split('/').pop() === 'index.html') {
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-links a[href^="#"]');
        
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (window.scrollY >= sectionTop - 100) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    }
});
