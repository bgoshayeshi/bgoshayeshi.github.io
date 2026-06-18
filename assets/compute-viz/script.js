(() => {
    // Subtle "load" flicker on the server chips so the single unit feels live.
    // Pure decoration; respects reduced-motion.
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');

    function init() {
        if (reduce.matches) return;
        const chips = Array.from(document.querySelectorAll('.chip'));
        if (!chips.length) return;

        const rand = (min, max) => min + Math.random() * (max - min);

        const tick = () => {
            const chip = chips[Math.floor(rand(0, chips.length))];
            chip.classList.add('busy');
            setTimeout(() => chip.classList.remove('busy'), rand(220, 620));
            setTimeout(tick, rand(500, 1800));
        };
        setTimeout(tick, rand(300, 1200));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
