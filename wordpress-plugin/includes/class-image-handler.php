<?php

namespace PixelVault;

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Handles image downloading, SEO renaming, and insertion into posts.
 */
class Image_Handler {

    private API_Client $api;

    public function __construct( API_Client $api ) {
        $this->api = $api;
    }

    /**
     * Insert a PixelVault image into a post.
     *
     * Downloads the image, gives it an SEO filename, adds it to the
     * Media Library, and optionally sets it as the featured image.
     *
     * @param string $image_id       PixelVault image UUID.
     * @param int    $post_id        WordPress post ID.
     * @param bool   $as_featured    Set as featured image.
     * @param array  $seo_context    {title, slug, focus_keyword} for SEO naming.
     * @return int|WP_Error          WordPress attachment ID on success.
     */
    public function insert_image( string $image_id, int $post_id, bool $as_featured = false, array $seo_context = array() ) {
        // 1. Get image metadata from backend.
        $meta = $this->api->get_image( $image_id );
        if ( is_wp_error( $meta ) ) {
            return $meta;
        }

        // 2. Download the raw image bytes.
        $bytes = $this->api->download_image( $image_id );
        if ( is_wp_error( $bytes ) ) {
            return $bytes;
        }

        // 3. Generate SEO filename.
        $seo_name = $this->generate_seo_filename( $meta, $seo_context );
        $ext      = $this->get_extension( $meta['filename'] ?? 'image.jpg' );
        $filename = $seo_name . '.' . $ext;

        // 4. Save to uploads directory.
        $upload = wp_upload_bits( $filename, null, $bytes );
        if ( ! empty( $upload['error'] ) ) {
            return new \WP_Error( 'pixelvault_upload_failed', $upload['error'] );
        }

        // 5. Create attachment in Media Library.
        $filetype   = wp_check_filetype( $upload['file'] );
        $attachment = array(
            'post_title'     => $this->humanize( $seo_name ),
            'post_content'   => '',
            'post_status'    => 'inherit',
            'post_mime_type' => $filetype['type'],
            'meta_input'     => array(
                '_pixelvault_image_id' => $image_id,
                '_pixelvault_source'   => 'auto',
            ),
        );

        $attach_id = wp_insert_attachment( $attachment, $upload['file'], $post_id );
        if ( is_wp_error( $attach_id ) ) {
            return $attach_id;
        }

        // Generate attachment metadata (thumbnails, sizes).
        require_once ABSPATH . 'wp-admin/includes/image.php';
        $attach_data = wp_generate_attachment_metadata( $attach_id, $upload['file'] );
        wp_update_attachment_metadata( $attach_id, $attach_data );

        // Set alt text from post title / SEO context.
        $alt = $seo_context['focus_keyword']
            ?? $seo_context['title']
            ?? $this->humanize( $seo_name );
        update_post_meta( $attach_id, '_wp_attachment_image_alt', sanitize_text_field( $alt ) );

        // 6. Set as featured image if requested.
        if ( $as_featured ) {
            set_post_thumbnail( $post_id, $attach_id );
        }

        // 7. Record deployment on backend.
        $post = get_post( $post_id );
        $this->api->record_deployment( $image_id, array(
            'site_url'       => home_url(),
            'post_id'        => $post_id,
            'post_title'     => $post->post_title ?? '',
            'local_filename' => $filename,
            'local_path'     => $upload['file'],
        ) );

        return $attach_id;
    }

    /**
     * Generate an SEO-friendly filename from post context.
     *
     * Priority: focus_keyword > title slug > industry-style fallback.
     */
    private function generate_seo_filename( array $image_meta, array $seo_context ): string {
        $parts = array();

        // Start with focus keyword or title.
        if ( ! empty( $seo_context['focus_keyword'] ) ) {
            $parts[] = sanitize_title( $seo_context['focus_keyword'] );
        } elseif ( ! empty( $seo_context['title'] ) ) {
            $parts[] = sanitize_title( $seo_context['title'] );
        }

        // Add industry context.
        if ( ! empty( $image_meta['industry'] ) ) {
            $parts[] = sanitize_title( $image_meta['industry'] );
        }

        // Add style if available.
        if ( ! empty( $image_meta['style'] ) && $image_meta['style'] !== 'general' ) {
            $parts[] = sanitize_title( $image_meta['style'] );
        }

        if ( empty( $parts ) ) {
            $parts[] = 'pixelvault-image';
        }

        // Truncate to reasonable length and add uniqueness.
        $slug = implode( '-', $parts );
        $slug = substr( $slug, 0, 80 );
        $slug .= '-' . substr( md5( $image_meta['id'] ?? uniqid() ), 0, 6 );

        return $slug;
    }

    /**
     * Get file extension from filename.
     */
    private function get_extension( string $filename ): string {
        $ext = strtolower( pathinfo( $filename, PATHINFO_EXTENSION ) );
        return in_array( $ext, array( 'jpg', 'jpeg', 'png', 'webp' ), true ) ? $ext : 'jpg';
    }

    /**
     * Convert slug to human-readable title.
     */
    private function humanize( string $slug ): string {
        return ucwords( str_replace( array( '-', '_' ), ' ', $slug ) );
    }
}
