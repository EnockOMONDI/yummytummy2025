/**
 * Expandable Product Previews JavaScript
 * Handles accordion-style expansion for product variant selection
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeExpandableCards();
});

function initializeExpandableCards() {
    const expandableCards = document.querySelectorAll('.expandable-card');
    
    expandableCards.forEach(card => {
        const expandBtn = card.querySelector('.expand-btn');
        const expandedSection = card.querySelector('.card-expanded');
        
        if (expandBtn && expandedSection) {
            expandBtn.addEventListener('click', function() {
                toggleCardExpansion(card, expandBtn, expandedSection);
            });
        }
        
        // Initialize quantity selectors for all forms in the card
        initializeQuantitySelectors(card);
        
        // Add click outside to close functionality
        document.addEventListener('click', function(event) {
            if (!card.contains(event.target) && card.classList.contains('expanded')) {
                collapseCard(card, expandBtn, expandedSection);
            }
        });
    });
}

function toggleCardExpansion(card, expandBtn, expandedSection) {
    const isExpanded = card.classList.contains('expanded');
    
    if (isExpanded) {
        collapseCard(card, expandBtn, expandedSection);
    } else {
        expandCard(card, expandBtn, expandedSection);
    }
}

function expandCard(card, expandBtn, expandedSection) {
    // Close other expanded cards first
    closeOtherExpandedCards(card);
    
    // Expand current card
    card.classList.add('expanded');
    expandBtn.classList.add('expanded');
    expandBtn.setAttribute('data-expanded', 'true');
    
    // Show expanded section with animation
    expandedSection.style.display = 'block';
    
    // Trigger reflow for animation
    expandedSection.offsetHeight;
    
    // Smooth scroll to card if needed
    setTimeout(() => {
        scrollToCardIfNeeded(card);
    }, 200);
    
    // Add escape key listener
    addEscapeKeyListener(card, expandBtn, expandedSection);
}

function collapseCard(card, expandBtn, expandedSection) {
    card.classList.remove('expanded');
    expandBtn.classList.remove('expanded');
    expandBtn.setAttribute('data-expanded', 'false');
    
    // Hide expanded section with animation
    expandedSection.style.animation = 'slideUp 0.3s ease-out';
    
    setTimeout(() => {
        expandedSection.style.display = 'none';
        expandedSection.style.animation = '';
    }, 300);
    
    // Remove escape key listener
    removeEscapeKeyListener();
}

function closeOtherExpandedCards(currentCard) {
    const allExpandedCards = document.querySelectorAll('.expandable-card.expanded');
    
    allExpandedCards.forEach(card => {
        if (card !== currentCard) {
            const expandBtn = card.querySelector('.expand-btn');
            const expandedSection = card.querySelector('.card-expanded');
            collapseCard(card, expandBtn, expandedSection);
        }
    });
}

function scrollToCardIfNeeded(card) {
    const cardRect = card.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    
    // Check if card is partially out of view
    if (cardRect.bottom > viewportHeight || cardRect.top < 0) {
        card.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
    }
}

function initializeQuantitySelectors(card) {
    const quantitySelectors = card.querySelectorAll('.quantity-selector');

    quantitySelectors.forEach(selector => {
        // Skip if already has handlers attached by main.js or expandable-cards.js
        if (selector.hasAttribute('data-handlers-attached') ||
            selector.hasAttribute('data-expandable-handlers-attached')) {
            return;
        }

        const minusBtn = selector.querySelector('.minus');
        const plusBtn = selector.querySelector('.plus');
        const quantityInput = selector.querySelector('input[name="quantity"]');

        if (minusBtn && plusBtn && quantityInput) {
            // Mark as having expandable handlers attached
            selector.setAttribute('data-expandable-handlers-attached', 'true');

            minusBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const currentValue = parseInt(quantityInput.value) || 1;
                if (currentValue > 1) {
                    quantityInput.value = currentValue - 1;
                    animateQuantityChange(quantityInput);
                }
            });

            plusBtn.addEventListener('click', function(e) {
                e.preventDefault();
                const currentValue = parseInt(quantityInput.value) || 1;
                quantityInput.value = currentValue + 1;
                animateQuantityChange(quantityInput);
            });

            // Ensure minimum value
            quantityInput.addEventListener('change', function() {
                const value = parseInt(this.value);
                if (isNaN(value) || value < 1) {
                    this.value = 1;
                }
            });
        }
    });
}

function animateQuantityChange(input) {
    input.style.transform = 'scale(1.1)';
    input.style.backgroundColor = 'rgba(255, 193, 7, 0.3)';
    
    setTimeout(() => {
        input.style.transform = 'scale(1)';
        input.style.backgroundColor = '';
    }, 200);
}

// Escape key functionality
let escapeKeyHandler = null;

function addEscapeKeyListener(card, expandBtn, expandedSection) {
    escapeKeyHandler = function(event) {
        if (event.key === 'Escape') {
            collapseCard(card, expandBtn, expandedSection);
        }
    };
    
    document.addEventListener('keydown', escapeKeyHandler);
}

function removeEscapeKeyListener() {
    if (escapeKeyHandler) {
        document.removeEventListener('keydown', escapeKeyHandler);
        escapeKeyHandler = null;
    }
}

// Add slideUp animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-20px);
        }
    }
`;
document.head.appendChild(style);

// Add variant card hover effects
function addVariantCardEffects() {
    const variantCards = document.querySelectorAll('.variant-card');
    
    variantCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
}

// Initialize variant card effects when cards are expanded
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('expand-btn')) {
        setTimeout(addVariantCardEffects, 400);
    }
});

// Export functions for potential external use
window.ExpandableCards = {
    initialize: initializeExpandableCards,
    expandCard: expandCard,
    collapseCard: collapseCard,
    closeOtherExpandedCards: closeOtherExpandedCards
};
