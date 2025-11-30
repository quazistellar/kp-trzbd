let isZoomed = false;
let lastScrollY = 0;
let lastScrollX = 0;

const handleZoom = () => {
  if (!window.visualViewport) return;

  const scale = window.visualViewport.scale;

  if (scale > 1) {
    if (!isZoomed) {
      lastScrollY = window.scrollY;
      lastScrollX = window.scrollX;

      document.body.style.position = 'fixed';
      document.body.style.top = `-${lastScrollY}px`;
      document.body.style.left = `-${lastScrollX}px`;
      document.body.style.width = '100%';
      document.body.style.overflow = 'hidden'; 

      document.body.classList.add('no-horizontal-scroll');

      isZoomed = true;
    }

    const currentTop = -parseInt(document.body.style.top || '0', 10);
    if (Math.abs(currentTop - lastScrollY) > 1) {
      document.body.style.top = `-${lastScrollY}px`;
    }
  }


  else if (isZoomed) {
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.width = '';
    document.body.style.overflow = '';

    document.body.classList.remove('no-horizontal-scroll');

    requestAnimationFrame(() => {
      window.scrollTo(lastScrollX, lastScrollY);
    });

    isZoomed = false;
  }
};

window.visualViewport.addEventListener('resize', handleZoom);

handleZoom();