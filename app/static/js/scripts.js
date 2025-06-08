document.addEventListener('DOMContentLoaded', function() {
    const filterForm = document.getElementById('filter-form');

    const applyFilters = () => {
        const ciudadId = document.getElementById('ciudad_id')?.value || '';
        const departamentoId = document.getElementById('departamento_id')?.value || '';
        const tipoOperacion = document.getElementById('tipo_operacion')?.value.toLowerCase() || '';
        const tipoPropiedad = document.getElementById('tipo_propiedad')?.value.toLowerCase() || '';
        const precioMin = parseFloat(document.getElementById('precio_min')?.value) || 0;
        const precioMax = parseFloat(document.getElementById('precio_max')?.value) || Number.MAX_VALUE;

        const landItems = document.querySelectorAll('.land-item');

        landItems.forEach(item => {
            const itemCiudad = item.dataset.ciudadId || '';
            const itemDepartamento = item.dataset.departamentoId || '';
            const itemOperacion = item.dataset.tipoOperacion?.toLowerCase() || 'indistinto';
            const itemPropiedad = item.dataset.tipoPropiedad?.toLowerCase() || 'indistinto';
            const itemPrecio = parseFloat(item.dataset.price) || 0;

            const matchesCiudad = !ciudadId || itemCiudad === ciudadId;
            const matchesDepartamento = !departamentoId || itemDepartamento === departamentoId;
            const matchesOperacion = tipoOperacion === 'indistinto' || itemOperacion === tipoOperacion;
            const matchesPropiedad = tipoPropiedad === 'indistinto' || itemPropiedad === tipoPropiedad;
            const matchesPrecio = itemPrecio >= precioMin && itemPrecio <= precioMax;

            if (matchesCiudad && matchesDepartamento && matchesOperacion && matchesPropiedad && matchesPrecio) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    };

    if (filterForm) {
        filterForm.addEventListener('submit', function(event) {
            event.preventDefault(); // Evita recargar la página
            applyFilters();
        });

        // También aplicar filtros al cambiar cualquier select o input
        const inputs = filterForm.querySelectorAll('select, input');
        inputs.forEach(input => {
            input.addEventListener('change', applyFilters);
        });
    }


    // --- Carousel and Lightbox Logic ---
    const carouselElement = document.querySelector('.image-gallery-carousel');
    if (carouselElement) {
        const mainImageElement = document.getElementById('carouselMainImage');
        const prevButtonElement = carouselElement.querySelector('.carousel-prev');
        const nextButtonElement = carouselElement.querySelector('.carousel-next');
        const imageListDivElement = carouselElement.querySelector('.carousel-image-list');
        
        // Extraer fuentes de imágenes y textos alternativos
        const imageSources = imageListDivElement ? Array.from(imageListDivElement.querySelectorAll('img')).map(img => ({src: img.src, alt: img.alt})) : [];
        let currentImageIdx = 0;

        function updateCarouselDisplay() {
            if (imageSources.length > 0 && mainImageElement) {
                mainImageElement.src = imageSources[currentImageIdx].src;
                mainImageElement.alt = imageSources[currentImageIdx].alt;
            } else if (mainImageElement && !mainImageElement.src) {
                // Si no hay imágenes y el src está vacío, podrías establecer un default aquí,
                // pero es mejor manejarlo en el HTML con Jinja.
                // mainImageElement.src = '/static/Img-prop/default.png'; // Ejemplo
                // mainImageElement.alt = 'Imagen no disponible';
            }
        }

        if (prevButtonElement && nextButtonElement && imageSources.length > 1) {
            prevButtonElement.addEventListener('click', function() {
                currentImageIdx = (currentImageIdx - 1 + imageSources.length) % imageSources.length;
                updateCarouselDisplay();
            });

            nextButtonElement.addEventListener('click', function() {
                currentImageIdx = (currentImageIdx + 1) % imageSources.length;
                updateCarouselDisplay();
            });
        } else if (prevButtonElement && nextButtonElement) { // Ocultar botones si no son necesarios
            prevButtonElement.style.display = 'none';
            nextButtonElement.style.display = 'none';
        }
        
        // Inicializar la primera imagen (ya se hace en HTML, pero esto es por si acaso)
        // updateCarouselDisplay(); // No es estrictamente necesario si el HTML ya pone la primera imagen

        // Lightbox functionality for the main carousel image
        const lightboxElement = document.getElementById('myImageLightbox');
        const lightboxImageElement = document.getElementById('lightboxImg');
        const lightboxCloseButton = lightboxElement ? lightboxElement.querySelector('.lightbox-close') : null;

        if (mainImageElement && lightboxElement && lightboxImageElement) {
            mainImageElement.addEventListener('click', function() {
                lightboxImageElement.src = this.src; // 'this' es mainImageElement
                lightboxImageElement.alt = this.alt;
                lightboxElement.style.display = 'flex';
            });
        }

        if (lightboxCloseButton) {
            lightboxCloseButton.addEventListener('click', function() {
                lightboxElement.style.display = 'none';
            });
        }

        if (lightboxElement) { // Cerrar al hacer clic en el fondo
            lightboxElement.addEventListener('click', function(event) {
                if (event.target === lightboxElement) {
                    lightboxElement.style.display = 'none';
                }
            });
        }
    } // Fin de if (carouselElement)
});

