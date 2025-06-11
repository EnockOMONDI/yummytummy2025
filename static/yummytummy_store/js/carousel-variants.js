/**
 * Carousel Variants JavaScript
 * Handles carousel navigation for product variant selection
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeCarouselVariants();
});

function initializeCarouselVariants() {
    const carouselCards = document.querySelectorAll('.carousel-card');
    
    carouselCards.forEach(card => {
        const productId = card.dataset.productId;
        const carousel = card.querySelector('.variant-carousel');
        const slides = card.querySelectorAll('.carousel-slide');
        const dots = card.querySelectorAll('.dot');
        const prevBtn = card.querySelector('.carousel-nav.prev');
        const nextBtn = card.querySelector('.carousel-nav.next');
        const autoCycleBtn = card.querySelector('.auto-cycle-btn');
        
        if (slides.length <= 1) return; // Skip if no variants
        
        let currentIndex = 0;
        let autoCycleInterval = null;
        let isAutoCycling = false;
        
        // Initialize carousel state
        const carouselState = {
            currentIndex: 0,
            totalSlides: slides.length,
            isTransitioning: false
        };
        
        // Navigation event listeners
        if (prevBtn) {
            prevBtn.addEventListener('click', () => navigateCarousel(card, carouselState, -1));
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => navigateCarousel(card, carouselState, 1));
        }
        
        // Dot navigation
        dots.forEach((dot, index) => {
            dot.addEventListener('click', () => goToSlide(card, carouselState, index));
        });
        
        // Auto-cycle functionality
        if (autoCycleBtn) {
            autoCycleBtn.addEventListener('click', () => toggleAutoCycle(card, carouselState));
        }
        
        // Touch/swipe support
        addTouchSupport(card, carouselState);
        
        // Keyboard navigation
        addKeyboardSupport(card, carouselState);
        
        // Initialize quantity selectors
        initializeQuantitySelector(card);
        
        // Set initial state
        updateCarouselDisplay(card, carouselState);
    });
}

function navigateCarousel(card, state, direction) {
    if (state.isTransitioning) return;
    
    const newIndex = (state.currentIndex + direction + state.totalSlides) % state.totalSlides;
    goToSlide(card, state, newIndex);
}

function goToSlide(card, state, targetIndex) {
    if (state.isTransitioning || targetIndex === state.currentIndex) return;
    
    state.isTransitioning = true;
    const previousIndex = state.currentIndex;
    state.currentIndex = targetIndex;
    
    // Update slides
    const slides = card.querySelectorAll('.carousel-slide');
    const dots = card.querySelectorAll('.dot');
    
    // Remove active classes
    slides[previousIndex].classList.remove('active');
    dots[previousIndex].classList.remove('active');
    
    // Add transition classes
    slides[previousIndex].classList.add('prev');
    slides[targetIndex].classList.add('active');
    dots[targetIndex].classList.add('active');
    
    // Update product info
    updateProductInfo(card, slides[targetIndex]);
    
    // Clean up transition classes
    setTimeout(() => {
        slides[previousIndex].classList.remove('prev');
        state.isTransitioning = false;
    }, 500);
    
    // Update carousel display
    updateCarouselDisplay(card, state);
}

function updateProductInfo(card, activeSlide) {
    const productId = card.dataset.productId;
    const price = parseFloat(activeSlide.dataset.price);
    const size = activeSlide.dataset.size;
    const variantId = activeSlide.dataset.variantId;
    
    // Update current size display
    const currentSizeElement = card.querySelector(`#current-size-${productId}`);
    if (currentSizeElement) {
        currentSizeElement.classList.add('updating');
        setTimeout(() => {
            currentSizeElement.textContent = size;
            currentSizeElement.classList.remove('updating');
        }, 150);
    }
    
    // Update price display
    const priceElement = card.querySelector(`#carousel-price-${productId}`);
    if (priceElement) {
        updatePriceDisplay(priceElement, price);
    }
    
    // Update add to cart button
    const addToCartBtn = card.querySelector('.add-to-cart.carousel');
    const currentSizeText = addToCartBtn.querySelector('.current-size-text');
    if (currentSizeText) {
        currentSizeText.textContent = size;
    }
    
    // Update hidden form input
    const variantInput = card.querySelector('.selected-variant-input');
    if (variantInput) {
        variantInput.value = variantId;
    }
}

function updatePriceDisplay(priceElement, price) {
    priceElement.classList.add('price-updating');
    
    setTimeout(() => {
        const amountElement = priceElement.querySelector('.amount');
        const decimalElement = priceElement.querySelector('.decimal');
        
        if (amountElement && decimalElement) {
            const formattedPrice = price.toFixed(2);
            const [wholePart, decimalPart] = formattedPrice.split('.');
            const formattedWhole = parseInt(wholePart).toLocaleString();
            
            amountElement.textContent = formattedWhole;
            decimalElement.textContent = '.' + decimalPart;
        }
        
        priceElement.classList.remove('price-updating');
    }, 200);
}

function toggleAutoCycle(card, state) {
    const autoCycleBtn = card.querySelector('.auto-cycle-btn');
    const isActive = autoCycleBtn.classList.contains('active');
    
    if (isActive) {
        stopAutoCycle(card);
        autoCycleBtn.classList.remove('active');
        autoCycleBtn.setAttribute('data-auto-cycle', 'false');
    } else {
        startAutoCycle(card, state);
        autoCycleBtn.classList.add('active');
        autoCycleBtn.setAttribute('data-auto-cycle', 'true');
    }
}

function startAutoCycle(card, state) {
    const interval = setInterval(() => {
        navigateCarousel(card, state, 1);
    }, 3000); // 3 seconds per slide
    
    card.autoCycleInterval = interval;
}

function stopAutoCycle(card) {
    if (card.autoCycleInterval) {
        clearInterval(card.autoCycleInterval);
        card.autoCycleInterval = null;
    }
}

function addTouchSupport(card, state) {
    let startX = 0;
    let startY = 0;
    let isSwipe = false;
    
    const carousel = card.querySelector('.variant-carousel');
    
    carousel.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        isSwipe = false;
    });
    
    carousel.addEventListener('touchmove', function(e) {
        if (!startX || !startY) return;
        
        const diffX = Math.abs(e.touches[0].clientX - startX);
        const diffY = Math.abs(e.touches[0].clientY - startY);
        
        if (diffX > diffY && diffX > 30) {
            isSwipe = true;
            e.preventDefault();
        }
    });
    
    carousel.addEventListener('touchend', function(e) {
        if (!isSwipe || !startX) return;
        
        const endX = e.changedTouches[0].clientX;
        const diffX = startX - endX;
        
        if (Math.abs(diffX) > 50) {
            if (diffX > 0) {
                navigateCarousel(card, state, 1); // Swipe left - next
            } else {
                navigateCarousel(card, state, -1); // Swipe right - prev
            }
        }
        
        startX = 0;
        startY = 0;
        isSwipe = false;
    });
}

function addKeyboardSupport(card, state) {
    card.addEventListener('keydown', function(e) {
        if (!card.contains(document.activeElement)) return;
        
        switch(e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                navigateCarousel(card, state, -1);
                break;
            case 'ArrowRight':
                e.preventDefault();
                navigateCarousel(card, state, 1);
                break;
            case ' ':
                e.preventDefault();
                toggleAutoCycle(card, state);
                break;
        }
    });
}

function updateCarouselDisplay(card, state) {
    const carousel = card.querySelector('.variant-carousel');
    carousel.setAttribute('data-current-index', state.currentIndex);
}

function initializeQuantitySelector(card) {
    const quantityInput = card.querySelector('input[name="quantity"]');
    const minusBtn = card.querySelector('.minus');
    const plusBtn = card.querySelector('.plus');
    
    if (minusBtn && plusBtn && quantityInput) {
        minusBtn.addEventListener('click', function() {
            const currentValue = parseInt(quantityInput.value) || 1;
            if (currentValue > 1) {
                quantityInput.value = currentValue - 1;
                animateQuantityChange(quantityInput);
            }
        });
        
        plusBtn.addEventListener('click', function() {
            const currentValue = parseInt(quantityInput.value) || 1;
            quantityInput.value = currentValue + 1;
            animateQuantityChange(quantityInput);
        });
        
        quantityInput.addEventListener('change', function() {
            const value = parseInt(this.value);
            if (isNaN(value) || value < 1) {
                this.value = 1;
            }
        });
    }
}

function animateQuantityChange(input) {
    input.style.transform = 'scale(1.1)';
    input.style.backgroundColor = 'rgba(255, 193, 7, 0.2)';
    
    setTimeout(() => {
        input.style.transform = 'scale(1)';
        input.style.backgroundColor = '';
    }, 200);
}

// Pause auto-cycle when page is not visible
document.addEventListener('visibilitychange', function() {
    const carouselCards = document.querySelectorAll('.carousel-card');
    
    carouselCards.forEach(card => {
        if (document.hidden) {
            stopAutoCycle(card);
        }
    });
});

// Export functions for potential external use
window.CarouselVariants = {
    initialize: initializeCarouselVariants,
    navigateCarousel: navigateCarousel,
    goToSlide: goToSlide,
    toggleAutoCycle: toggleAutoCycle
};
