(() => {
    const rand = (min, max) => min + Math.random() * (max - min);

    function spawnPacket(wire) {
        const p = document.createElement('span');
        p.className = 'packet';

        const duration = rand(0.9, 2.8);
        const width = rand(8, 22);
        const height = rand(2.5, 5);
        const opacity = rand(0.7, 1);

        p.style.animationDuration = duration.toFixed(2) + 's';
        p.style.animationDelay = '0s';
        p.style.animationIterationCount = '1';
        p.style.width = width.toFixed(1) + 'px';
        p.style.height = height.toFixed(1) + 'px';
        p.style.opacity = opacity.toFixed(2);

        wire.appendChild(p);
        p.addEventListener('animationend', () => p.remove(), { once: true });

        // Hard cleanup safeguard if animationend doesn't fire
        setTimeout(() => p.remove(), (duration + 0.5) * 1000);
    }

    function startStream(wire) {
        const tick = () => {
            spawnPacket(wire);
            // Random gap before next packet - independently per lane
            const next = rand(140, 1400);
            setTimeout(tick, next);
        };
        // Stagger lanes so they don't all fire on frame 1
        setTimeout(tick, rand(0, 900));
    }

    function init() {
        document.querySelectorAll('.wire').forEach(startStream);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
