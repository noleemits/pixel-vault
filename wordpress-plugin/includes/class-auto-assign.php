<?php

namespace PixelVault;

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Auto-assign engine.
 *
 * Analyses post content on save and matches/suggests images from the library.
 * Hooks into `save_post` to auto-set featured images.
 */
class Auto_Assign {

    private API_Client $api;
    private Image_Handler $handler;

    /** Prevent recursive saves. */
    private static bool $saving = false;

    public function __construct( API_Client $api, Image_Handler $handler ) {
        $this->api     = $api;
        $this->handler = $handler;
    }

    /**
     * WordPress save_post callback.
     *
     * @param int      $post_id Post ID.
     * @param \WP_Post $post    Post object.
     * @param bool     $update  Whether this is an update.
     */
    public function on_save_post( int $post_id, \WP_Post $post, bool $update ): void {
        // Guards.
        if ( self::$saving ) {
            return;
        }
        if ( defined( 'DOING_AUTOSAVE' ) && DOING_AUTOSAVE ) {
            return;
        }
        if ( wp_is_post_revision( $post_id ) || wp_is_post_autosave( $post_id ) ) {
            return;
        }
        if ( ! current_user_can( 'edit_post', $post_id ) ) {
            return;
        }
        if ( ! in_array( $post->post_type, $this->supported_post_types(), true ) ) {
            return;
        }

        $opts = get_option( 'pixelvault_settings', array() );
        if ( empty( $opts['auto_assign'] ) || ! $this->api->is_connected() ) {
            return;
        }

        // Skip if post already has a featured image.
        if ( has_post_thumbnail( $post_id ) ) {
            return;
        }

        // Build post context.
        $context = $this->extract_context( $post );

        // Ask backend for a match.
        $result = $this->api->match_images( $context );
        if ( is_wp_error( $result ) || empty( $result['matches'] ) ) {
            // No match — store suggestion for notification system.
            if ( ! is_wp_error( $result ) && ! empty( $result['suggested_prompt'] ) ) {
                update_post_meta( $post_id, '_pixelvault_suggested_prompt', sanitize_text_field( $result['suggested_prompt'] ) );
                update_post_meta( $post_id, '_pixelvault_no_match', '1' );
            }
            return;
        }

        $best = $result['matches'][0];

        // High confidence — auto-assign silently.
        if ( ( $best['confidence'] ?? 0 ) >= 0.8 ) {
            self::$saving = true;
            $this->handler->insert_image(
                $best['image_id'],
                $post_id,
                true, // as featured
                array(
                    'title'         => $post->post_title,
                    'slug'          => $post->post_name,
                    'focus_keyword' => $context['focus_keyword'] ?? '',
                )
            );
            delete_post_meta( $post_id, '_pixelvault_no_match' );
            delete_post_meta( $post_id, '_pixelvault_suggested_prompt' );
            self::$saving = false;
            return;
        }

        // Medium confidence — store suggestions for the notification system to show.
        $suggestions = array_slice( $result['matches'], 0, 3 );
        update_post_meta( $post_id, '_pixelvault_suggestions', wp_json_encode( $suggestions ) );
        delete_post_meta( $post_id, '_pixelvault_no_match' );
    }

    /**
     * Extract post context for matching.
     *
     * Pulls from title, slug, categories, tags, and SEO plugin keywords.
     *
     * @return array Context payload for the /match endpoint.
     */
    public function extract_context( \WP_Post $post ): array {
        $context = array(
            'title'      => $post->post_title,
            'slug'       => $post->post_name,
            'content'    => wp_trim_words( wp_strip_all_tags( $post->post_content ), 100, '' ),
            'categories' => array(),
            'tags'       => array(),
        );

        // Categories.
        $cats = get_the_category( $post->ID );
        if ( $cats ) {
            $context['categories'] = wp_list_pluck( $cats, 'name' );
        }

        // Tags.
        $tags = get_the_tags( $post->ID );
        if ( $tags ) {
            $context['tags'] = wp_list_pluck( $tags, 'name' );
        }

        // Yoast SEO focus keyword.
        $yoast_kw = get_post_meta( $post->ID, '_yoast_wpseo_focuskw', true );
        if ( $yoast_kw ) {
            $context['focus_keyword'] = $yoast_kw;
        }

        // RankMath focus keyword.
        if ( empty( $context['focus_keyword'] ) ) {
            $rank_kw = get_post_meta( $post->ID, 'rank_math_focus_keyword', true );
            if ( $rank_kw ) {
                $context['focus_keyword'] = explode( ',', $rank_kw )[0];
            }
        }

        return $context;
    }

    /**
     * Post types that support auto-assign.
     */
    private function supported_post_types(): array {
        return apply_filters( 'pixelvault_auto_assign_post_types', array( 'post', 'page' ) );
    }
}
