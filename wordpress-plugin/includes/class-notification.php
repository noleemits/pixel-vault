<?php

namespace PixelVault;

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Admin notification system.
 *
 * Shows toasts and suggestion panels when:
 * - Auto-assign found suggestions (medium confidence)
 * - No match found (offers to generate)
 * - Image was auto-assigned (confirmation)
 */
class Notification {

    /**
     * Hook into admin.
     */
    public function register(): void {
        add_action( 'admin_notices', array( $this, 'render_post_notices' ) );
        add_action( 'admin_footer', array( $this, 'render_toast_container' ) );
    }

    /**
     * Show PixelVault notices on post edit screens.
     */
    public function render_post_notices(): void {
        $screen = get_current_screen();
        if ( ! $screen || $screen->base !== 'post' ) {
            return;
        }

        $post_id = get_the_ID();
        if ( ! $post_id ) {
            return;
        }

        // Check for suggestions (medium confidence matches).
        $suggestions = get_post_meta( $post_id, '_pixelvault_suggestions', true );
        if ( $suggestions ) {
            $items = json_decode( $suggestions, true );
            if ( is_array( $items ) && count( $items ) > 0 ) {
                $this->render_suggestion_notice( $post_id, $items );
                return;
            }
        }

        // Check for no-match with generation suggestion.
        $no_match = get_post_meta( $post_id, '_pixelvault_no_match', true );
        if ( $no_match ) {
            $prompt = get_post_meta( $post_id, '_pixelvault_suggested_prompt', true );
            $this->render_generate_notice( $post_id, $prompt );
        }
    }

    /**
     * Render suggestion notice — show top 3 image candidates.
     */
    private function render_suggestion_notice( int $post_id, array $suggestions ): void {
        ?>
        <div class="notice notice-info is-dismissible pixelvault-notice" id="pv-suggestion-notice">
            <div class="pv-notice-header">
                <strong><?php esc_html_e( 'PixelVault found images for this post', 'pixelvault' ); ?></strong>
            </div>
            <div class="pv-suggestion-grid">
                <?php foreach ( $suggestions as $s ) : ?>
                    <div class="pv-suggestion-item" data-image-id="<?php echo esc_attr( $s['image_id'] ); ?>">
                        <img
                            src="<?php echo esc_url( rest_url( 'pixelvault/v1/images/' . $s['image_id'] . '/file' ) ); ?>"
                            alt=""
                            loading="lazy"
                            style="max-width:200px;height:auto;border-radius:4px;cursor:pointer;"
                        >
                        <div class="pv-suggestion-meta">
                            <span class="pv-confidence"><?php echo esc_html( round( ( $s['confidence'] ?? 0 ) * 100 ) ); ?>% match</span>
                        </div>
                        <button type="button" class="button button-small pv-use-image" data-image-id="<?php echo esc_attr( $s['image_id'] ); ?>" data-post-id="<?php echo esc_attr( $post_id ); ?>">
                            <?php esc_html_e( 'Use as Featured', 'pixelvault' ); ?>
                        </button>
                    </div>
                <?php endforeach; ?>
            </div>
            <p>
                <a href="#" class="pv-browse-all"><?php esc_html_e( 'Browse full library', 'pixelvault' ); ?></a>
                &nbsp;|&nbsp;
                <a href="#" class="pv-dismiss-suggestions" data-post-id="<?php echo esc_attr( $post_id ); ?>"><?php esc_html_e( 'Dismiss', 'pixelvault' ); ?></a>
            </p>
        </div>
        <?php
    }

    /**
     * Render generate notice — no match found, suggest prompt.
     */
    private function render_generate_notice( int $post_id, string $prompt ): void {
        ?>
        <div class="notice notice-warning is-dismissible pixelvault-notice" id="pv-generate-notice">
            <div class="pv-notice-header">
                <strong><?php esc_html_e( 'PixelVault couldn\'t find a matching image', 'pixelvault' ); ?></strong>
            </div>
            <?php if ( $prompt ) : ?>
                <p><?php esc_html_e( 'Suggested prompt:', 'pixelvault' ); ?></p>
                <div class="pv-prompt-preview">
                    <textarea id="pv-generate-prompt" class="large-text" rows="3"><?php echo esc_textarea( $prompt ); ?></textarea>
                </div>
                <p>
                    <button type="button" class="button button-primary pv-generate-btn" data-post-id="<?php echo esc_attr( $post_id ); ?>">
                        <?php esc_html_e( 'Generate SD — included in plan', 'pixelvault' ); ?>
                    </button>
                    <button type="button" class="button pv-generate-btn pv-generate-hq" data-post-id="<?php echo esc_attr( $post_id ); ?>" data-quality="hq">
                        <?php esc_html_e( 'Generate HQ — $0.05', 'pixelvault' ); ?>
                    </button>
                    &nbsp;
                    <a href="#" class="pv-browse-all"><?php esc_html_e( 'Browse library instead', 'pixelvault' ); ?></a>
                </p>
            <?php else : ?>
                <p>
                    <?php esc_html_e( 'Try browsing the library or generating a custom image.', 'pixelvault' ); ?>
                    <a href="#" class="pv-browse-all"><?php esc_html_e( 'Open PixelVault', 'pixelvault' ); ?></a>
                </p>
            <?php endif; ?>
        </div>
        <?php
    }

    /**
     * Render the toast container in the admin footer.
     */
    public function render_toast_container(): void {
        ?>
        <div id="pv-toast-container" style="position:fixed;bottom:20px;right:20px;z-index:999999;"></div>
        <?php
    }
}
