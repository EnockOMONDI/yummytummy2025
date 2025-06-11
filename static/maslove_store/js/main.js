document.addEventListener('DOMContentLoaded', function() {
    // Message dismissal
    const messages = document.querySelectorAll('.message');
    messages.forEach(message => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            message.style.opacity = '0';
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000);

        // Manual dismiss with close button
        const closeBtn = message.querySelector('.close-message');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                message.style.opacity = '0';
                setTimeout(() => {
                    message.remove();
                }, 300);
            });
        }
    });
    // Mobile Menu Toggle
    const menuToggle = document.querySelector('.menu-toggle');
    const mobileNav = document.querySelector('.mobile-nav');

    if (menuToggle && mobileNav) {
        menuToggle.addEventListener('click', function() {
            mobileNav.classList.toggle('active');

            // Animate hamburger to X
            const spans = menuToggle.querySelectorAll('span');
            if (mobileNav.classList.contains('active')) {
                spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
                spans[1].style.opacity = '0';
                spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
            } else {
                spans[0].style.transform = 'none';
                spans[1].style.opacity = '1';
                spans[2].style.transform = 'none';
            }
        });
    }

    // Hero Slider
    const slides = document.querySelectorAll('.slide');
    const prevButton = document.querySelector('.prev-slide');
    const nextButton = document.querySelector('.next-slide');
    let currentSlide = 0;

    function showSlide(index) {
        slides.forEach(slide => slide.classList.remove('active'));

        if (index < 0) {
            currentSlide = slides.length - 1;
        } else if (index >= slides.length) {
            currentSlide = 0;
        } else {
            currentSlide = index;
        }

        slides[currentSlide].classList.add('active');

        // Update slider controls
        const controls = document.querySelectorAll('.slider-controls button');
        if (controls.length) {
            controls.forEach((control, i) => {
                control.classList.toggle('active', i === currentSlide);
            });
        }
    }

    if (prevButton && nextButton && slides.length) {
        prevButton.addEventListener('click', () => showSlide(currentSlide - 1));
        nextButton.addEventListener('click', () => showSlide(currentSlide + 1));

        // Create slider controls if they don't exist
        const sliderControls = document.querySelector('.slider-controls');
        if (sliderControls && !sliderControls.children.length) {
            for (let i = 0; i < slides.length; i++) {
                const control = document.createElement('button');
                control.setAttribute('aria-label', `Go to slide ${i + 1}`);
                control.addEventListener('click', () => showSlide(i));
                sliderControls.appendChild(control);
            }

            // Set initial active control
            if (sliderControls.children.length) {
                sliderControls.children[0].classList.add('active');
            }
        }

        // Auto-rotate slides every 5 seconds
        setInterval(() => showSlide(currentSlide + 1), 5000);
    }

    // Quantity Selectors
    const quantitySelectors = document.querySelectorAll('.quantity-selector');

    quantitySelectors.forEach(selector => {
        const minusButton = selector.querySelector('.minus');
        const plusButton = selector.querySelector('.plus');
        const input = selector.querySelector('input');

        if (minusButton && plusButton && input) {
            minusButton.addEventListener('click', () => {
                let value = parseInt(input.value);
                if (value > 1) {
                    input.value = value - 1;

                    // If in cart, auto-submit the form for immediate update
                    const updateForm = selector.closest('.update-form');
                    if (updateForm) {
                        updateForm.submit();
                    }
                }
            });

            plusButton.addEventListener('click', () => {
                let value = parseInt(input.value);
                input.value = value + 1;

                // If in cart, auto-submit the form for immediate update
                const updateForm = selector.closest('.update-form');
                if (updateForm) {
                    updateForm.submit();
                }
            });

            input.addEventListener('change', () => {
                let value = parseInt(input.value);
                if (isNaN(value) || value < 1) {
                    input.value = 1;
                }

                // If in cart, auto-submit the form for immediate update
                const updateForm = selector.closest('.update-form');
                if (updateForm) {
                    updateForm.submit();
                }
            });
        }
    });

    // Add to Cart Animation
    const addToCartButtons = document.querySelectorAll('.add-to-cart');
    const cartCount = document.querySelector('.cart-count');

    addToCartButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Check if we're on the product detail page or product list page
            const isProductDetail = this.closest('.product-detail') !== null;
            const isProductPreview = this.closest('.product-preview') !== null;
            const isHighlightedProduct = this.closest('.highlighted-product') !== null;

            // Only prevent default for product preview (list page) but NOT for highlighted product
            // Allow normal form submission for product detail page and highlighted product
            if (!isProductDetail && !isHighlightedProduct) {
                e.preventDefault();
            }

            // Get product info and perform animation
            let productImage, quantity;

            if (isProductDetail) {
                // Product detail page
                const productDetailContainer = this.closest('.product-detail');
                productImage = productDetailContainer.querySelector('.product-detail-image');
                quantity = productDetailContainer.querySelector('.quantity-selector input');
            } else if (isProductPreview) {
                // Product list page
                const productContainer = this.closest('.product-preview');
                productImage = productContainer.querySelector('img');
                quantity = productContainer.querySelector('.quantity-selector input');
            } else if (isHighlightedProduct) {
                // Highlighted product on homepage
                const productContainer = this.closest('.highlighted-product');
                productImage = productContainer.querySelector('img');
                quantity = productContainer.querySelector('.quantity-selector input');
            } else {
                // Neither product detail, preview, nor highlighted product found
                if (isProductDetail || isHighlightedProduct) {
                    // If on product detail page or highlighted product, allow form submission
                    return true;
                } else {
                    return;
                }
            }

            if (productImage && cartCount) {
                // Create flying image
                const flyingImage = productImage.cloneNode();
                flyingImage.style.position = 'fixed';
                flyingImage.style.zIndex = '1000';
                flyingImage.style.width = '100px';
                flyingImage.style.opacity = '0.8';
                flyingImage.style.transition = 'all 1s ease';

                // Get positions
                const imgRect = productImage.getBoundingClientRect();
                const cartRect = cartCount.getBoundingClientRect();

                // Set initial position
                flyingImage.style.top = imgRect.top + 'px';
                flyingImage.style.left = imgRect.left + 'px';

                // Append to body
                document.body.appendChild(flyingImage);

                // Trigger animation
                setTimeout(() => {
                    flyingImage.style.top = cartRect.top + 'px';
                    flyingImage.style.left = cartRect.left + 'px';
                    flyingImage.style.width = '20px';
                    flyingImage.style.opacity = '0.2';
                }, 10);

                // Remove flying image and update cart
                setTimeout(() => {
                    document.body.removeChild(flyingImage);

                    // Update cart count
                    let count = parseInt(cartCount.textContent) || 0;
                    let addQuantity = quantity ? parseInt(quantity.value) : 1;
                    cartCount.textContent = count + addQuantity;

                    // Show confirmation message
                    const message = document.createElement('div');
                    message.textContent = 'Product added to cart';
                    message.style.position = 'fixed';
                    message.style.top = '20px';
                    message.style.left = '50%';
                    message.style.transform = 'translateX(-50%)';
                    message.style.backgroundColor = 'var(--primary-color)';
                    message.style.color = 'var(--secondary-color)';
                    message.style.padding = '10px 20px';
                    message.style.borderRadius = '5px';
                    message.style.zIndex = '1001';

                    document.body.appendChild(message);

                    setTimeout(() => {
                        document.body.removeChild(message);
                    }, 3000);

                    // If on product detail page or highlighted product, submit the form
                    if (isProductDetail || isHighlightedProduct) {
                        const form = this.closest('form');
                        if (form) {
                            form.submit();
                        }
                    }
                }, 1000);
            } else if (isProductDetail || isHighlightedProduct) {
                // If on product detail page or highlighted product but couldn't find image, still submit the form
                const form = this.closest('form');
                if (form) {
                    form.submit();
                }
            }
        });
    });
});
