/**
 * PixelVault — Admin JS.
 *
 * Handles: toast notifications, suggestion interactions, generate buttons.
 */
(function () {
    'use strict';

    const API = window.pixelvaultAdmin;
    if (!API) return;

    // -----------------------------------------------------------------
    // Toast system
    // -----------------------------------------------------------------

    function toast(message, type = 'info') {
        const container = document.getElementById('pv-toast-container');
        if (!container) return;

        const el = document.createElement('div');
        el.className = `pv-toast pv-toast--${type}`;
        el.textContent = message;
        container.appendChild(el);

        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(20px)';
            el.style.transition = 'all 0.3s ease-out';
            setTimeout(() => el.remove(), 300);
        }, 4000);
    }

    window.pvToast = toast;

    // -----------------------------------------------------------------
    // REST helper
    // -----------------------------------------------------------------

    async function pvFetch(endpoint, options = {}) {
        const resp = await fetch(API.restUrl + endpoint, {
            headers: {
                'X-WP-Nonce': API.nonce,
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });
        return resp.json();
    }

    // -----------------------------------------------------------------
    // Suggestion notice — "Use as Featured" button
    // -----------------------------------------------------------------

    document.addEventListener('click', async function (e) {
        const btn = e.target.closest('.pv-use-image');
        if (!btn) return;

        e.preventDefault();
        btn.disabled = true;
        btn.textContent = 'Inserting...';

        const imageId = btn.dataset.imageId;
        const postId = btn.dataset.postId;

        try {
            const result = await pvFetch('insert', {
                method: 'POST',
                body: JSON.stringify({
                    image_id: imageId,
                    post_id: parseInt(postId, 10),
                    as_featured: true,
                }),
            });

            if (result.error) {
                toast(result.error, 'error');
                btn.disabled = false;
                btn.textContent = 'Use as Featured';
                return;
            }

            toast(result.message || 'Featured image set!', 'success');

            // Remove the suggestion notice.
            const notice = document.getElementById('pv-suggestion-notice');
            if (notice) notice.remove();

            // Refresh the featured image meta box if possible.
            if (window.wp && wp.data) {
                wp.data.dispatch('core/editor').editPost({ featured_media: result.attachment_id });
            }
        } catch (err) {
            toast('Failed to insert image.', 'error');
            btn.disabled = false;
            btn.textContent = 'Use as Featured';
        }
    });

    // -----------------------------------------------------------------
    // Generate button
    // -----------------------------------------------------------------

    document.addEventListener('click', async function (e) {
        const btn = e.target.closest('.pv-generate-btn');
        if (!btn) return;

        e.preventDefault();
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Generating...';

        const postId = btn.dataset.postId;
        const quality = btn.dataset.quality || 'sd';
        const promptEl = document.getElementById('pv-generate-prompt');
        const prompt = promptEl ? promptEl.value : '';

        if (!prompt.trim()) {
            toast('Please enter a prompt.', 'error');
            btn.disabled = false;
            btn.textContent = originalText;
            return;
        }

        try {
            const result = await pvFetch('generate', {
                method: 'POST',
                body: JSON.stringify({
                    prompt: prompt.trim(),
                    post_id: parseInt(postId, 10),
                    quality: quality,
                }),
            });

            if (result.error) {
                toast(result.error, 'error');
            } else {
                toast(result.message || 'Image generation started!', 'success');
                const notice = document.getElementById('pv-generate-notice');
                if (notice) notice.remove();
            }
        } catch (err) {
            toast('Generation request failed.', 'error');
        }

        btn.disabled = false;
        btn.textContent = originalText;
    });

    // -----------------------------------------------------------------
    // Dismiss suggestions
    // -----------------------------------------------------------------

    document.addEventListener('click', function (e) {
        const link = e.target.closest('.pv-dismiss-suggestions');
        if (!link) return;

        e.preventDefault();
        const notice = document.getElementById('pv-suggestion-notice');
        if (notice) notice.remove();
    });

    // -----------------------------------------------------------------
    // Browse all — open Gutenberg sidebar
    // -----------------------------------------------------------------

    document.addEventListener('click', function (e) {
        const link = e.target.closest('.pv-browse-all');
        if (!link) return;

        e.preventDefault();
        // Open the PixelVault sidebar in Gutenberg if available.
        if (window.wp && wp.data) {
            wp.data.dispatch('core/edit-post').openGeneralSidebar('pixelvault-sidebar/pixelvault-sidebar');
        }
    });

})();
