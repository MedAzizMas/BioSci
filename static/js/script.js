document.addEventListener('DOMContentLoaded', () => {
    // Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    const html = document.documentElement;
    
    // Check for saved theme preference or default to light
    const savedTheme = localStorage.getItem('biosci-theme') || 'light';
    html.setAttribute('data-theme', savedTheme);
    
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('biosci-theme', newTheme);
        });
    }

    // Mobile Navigation Toggle
    const mobileToggle = document.querySelector('.mobile-toggle');
    const navLinks = document.querySelector('.nav-links');

    if (mobileToggle) {
        mobileToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');

            // Switch icon
            const icon = mobileToggle.querySelector('i');
            if (navLinks.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    }

    // Close mobile menu when clicking a link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            if (navLinks.classList.contains('active')) {
                navLinks.classList.remove('active');
                const icon = mobileToggle.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    });

    // Navbar Scroll Effect
    const navbar = document.querySelector('.navbar');

    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Smooth Scroll for Anchor Links (Optional fix for some browsers)
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                // Adjust for fixed header
                const headerOffset = 80;
                const elementPosition = target.getBoundingClientRect().top;
                const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: "smooth"
                });
            }
        });
    });

    // DNA Animation
    const canvas = document.getElementById('bioCanvas');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        let width, height;

        function resize() {
            width = canvas.width = canvas.offsetWidth;
            height = canvas.height = canvas.offsetHeight;
        }
        window.addEventListener('resize', resize);
        resize();

        // DNA Parameters
        const particles = [];
        const numBasePairs = 40;
        const radius = 100;
        const speed = 0.02;
        let angleOffset = 0;

        class Particle {
            constructor(y, angle, isStrand1) {
                this.y = y;
                this.angle = angle;
                this.isStrand1 = isStrand1;
            }

            draw(ctx, width, height, angleOffset) {
                const perspective = 300;
                const currentAngle = this.angle + angleOffset;
                const xBase = Math.cos(currentAngle) * radius;
                const zBase = Math.sin(currentAngle) * radius;

                // 3D Projection
                const scale = perspective / (perspective + zBase + 400); // 400 moves it back
                const x2d = width / 2 + xBase * scale;
                const y2d = this.y // Vertical position stays mostly relative to container, no y-projection needed for simple cylinder

                // Color & Opacity based on depth (z)
                const alpha = Math.max(0.1, (scale - 0.2));
                const color = this.isStrand1 ? `rgba(67, 97, 238, ${alpha})` : `rgba(114, 9, 183, ${alpha})`; // Primary & Secondary colors

                ctx.beginPath();
                ctx.arc(x2d, y2d, 4 * scale, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();

                return { x: x2d, y: y2d, scale, z: zBase };
            }
        }

        // Initialize Particles
        for (let i = 0; i < numBasePairs; i++) {
            const y = (height / numBasePairs) * i * 0.8 + (height * 0.1); // Spread vertically
            const angle = (i * 0.5);
            particles.push(new Particle(y, angle, true));  // Strand 1
            particles.push(new Particle(y, angle + Math.PI, false)); // Strand 2 (180 deg offset)
        }

        function animate() {
            ctx.clearRect(0, 0, width, height);

            angleOffset += speed;

            // Sort particles by Z depth so front ones draw on top
            // To do this properly we need to compute position first
            // But for simple dots, drawing order matters less than lines.
            // Let's draw connections first.

            for (let i = 0; i < particles.length; i += 2) {
                const p1 = particles[i];
                const p2 = particles[i + 1];

                // Calculate positions but don't draw yet
                // We'll just draw lines between pairs
                // Note: This simple loop re-calculates projection which is redundant but fine for 40 pairs.

                const perspective = 300;
                const currentAngle = p1.angle + angleOffset;
                const zBase = Math.sin(currentAngle) * radius;
                const scale = perspective / (perspective + zBase + 400);

                // Optimization: Only draw lines if not too deep? Or just fade them.
                if (scale > 0.3) {
                    // Calculate connecting line coordinates
                    // ... (Re-using logic from draw method is messy, let's just do it simply inside loop)
                }
            }

            // Simple render loop
            for (let i = 0; i < particles.length; i += 2) {
                const p1 = particles[i];
                const p2 = particles[i + 1];

                const pos1 = p1.draw(ctx, width, height, angleOffset);
                const pos2 = p2.draw(ctx, width, height, angleOffset);

                // Draw connection (Base Pair)
                ctx.beginPath();
                ctx.moveTo(pos1.x, pos1.y);
                ctx.lineTo(pos2.x, pos2.y);
                ctx.strokeStyle = `rgba(255, 255, 255, ${Math.min(pos1.scale, pos2.scale) * 0.1})`;
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            requestAnimationFrame(animate);
        }

        animate();
    }

    // Scroll Animations (Intersection Observer)
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target); // Animate once
            }
        });
    }, observerOptions);

    const animatedElements = document.querySelectorAll('.animate-on-scroll, .scale-up, .slide-left, .slide-right, .fade-in');
    animatedElements.forEach(el => observer.observe(el));

    // Marquee Scroll Logic
    const marqueeTrack = document.querySelector('.marquee-track');
    if (marqueeTrack) {
        let currentScroll = window.scrollY;
        let offset = 0;
        const baseSpeed = 1.0; // Steady baseline speed
        let currentSpeed = baseSpeed;

        // Clone items to ensure infinite loop
        const trackContent = marqueeTrack.innerHTML;
        marqueeTrack.innerHTML += trackContent + trackContent;

        function animateMarquee() {
            const targetScroll = window.scrollY;
            const scrollDelta = targetScroll - currentScroll;
            currentScroll = targetScroll; // Update for next frame

            // Smoother Acceleration Logic
            // Instead of instantaneous speed change, we target a speed and interpolate
            // But user said "just moving faster". 
            // We'll add a fraction of the scroll velocity to the speed.

            // To be "smooth", we shouldn't let speed jump. 
            // scrollDelta can be large. Let's dampen it or cap it, or accumulate momentum.
            // Simple approach: Speed = Base + (Factor * |Delta|)
            // But we apply it smoothly.

            const targetSpeedBoost = Math.abs(scrollDelta) * 0.5; // Sensitivity

            // If tracking scroll exactly is jittery, use linear interpolation for speed
            // currentSpeed approaches (baseSpeed + boost)
            currentSpeed += ((baseSpeed + targetSpeedBoost) - currentSpeed) * 0.1;

            // Prevent it from stopping or reversing if logic gets weird
            if (currentSpeed < baseSpeed) currentSpeed = baseSpeed;

            offset -= currentSpeed;

            // Reset logic 
            // Since we have plenty of duplicates, we reset when we cover 1/3
            if (Math.abs(offset) >= marqueeTrack.scrollWidth / 3) {
                offset = 0;
            }

            marqueeTrack.style.transform = `translateX(${offset}px)`;
            requestAnimationFrame(animateMarquee);
        }

        animateMarquee();
    }

    // Horizontal Scroll Gallery Logic
    const scrollSection = document.querySelector('.scroll-gallery-section');
    const rowLeft = document.querySelector('.row-left');
    const rowRight = document.querySelector('.row-right');

    if (scrollSection && rowLeft && rowRight) {
        window.addEventListener('scroll', () => {
            const sectionTop = scrollSection.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;

            // Start expecting scroll when section is nearing view
            if (sectionTop < windowHeight && sectionTop > -scrollSection.offsetHeight) {
                // Calculate scroll progress relative to the section
                const scrollProgress = (windowHeight - sectionTop) * 0.5;

                // Move rows in opposite directions
                // rowLeft moves left (negative translateX)
                rowLeft.style.transform = `translateX(-${scrollProgress}px)`;

                // rowRight moves right (positive translateX)
                // Start from significant negative offset so it interpolates into view or just moves differently
                // Actually, standard parallax moves it:
                rowRight.style.transform = `translateX(${scrollProgress - 800}px)`;
            }
        });
    }

    // FAQ Accordion Logic
    const faqItems = document.querySelectorAll('.faq-item');

    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');

        if (question) {
            question.addEventListener('click', () => {
                // Close all other items
                faqItems.forEach(otherItem => {
                    if (otherItem !== item && otherItem.classList.contains('active')) {
                        otherItem.classList.remove('active');
                    }
                });

                // Toggle current item
                item.classList.toggle('active');
            });
        }
    });
});
