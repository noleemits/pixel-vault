<?php

namespace PixelVault;

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * HTTP client for the PixelVault backend API.
 *
 * Uses wp_remote_* functions (WordPress HTTP API) — no cURL dependency.
 */
class API_Client {

    private string $api_url;
    private string $api_key;

    public function __construct() {
        $opts          = get_option( 'pixelvault_settings', array() );
        $this->api_url = untrailingslashit( $opts['api_url'] ?? 'http://localhost:8000/api/v1' );
        $this->api_key = $opts['api_key'] ?? '';
    }

    /**
     * Check if the plugin is connected (API key set).
     */
    public function is_connected(): bool {
        return ! empty( $this->api_key );
    }

    /**
     * Test the connection to the backend.
     *
     * @return array{ok: bool, message: string}
     */
    public function test_connection(): array {
        $response = $this->get( '/stats' );

        if ( is_wp_error( $response ) ) {
            return array(
                'ok'      => false,
                'message' => $response->get_error_message(),
            );
        }

        return array(
            'ok'      => true,
            'message' => sprintf(
                /* translators: %d: total images in the library */
                __( 'Connected — %d images in library.', 'pixelvault' ),
                $response['total'] ?? 0
            ),
        );
    }

    // -----------------------------------------------------------------
    // Images
    // -----------------------------------------------------------------

    /**
     * Browse images with filters.
     *
     * @param array $filters Optional filters: industry, style, ratio, status, page, per_page.
     * @return array|WP_Error
     */
    public function get_images( array $filters = array() ) {
        $defaults = array(
            'page'     => 1,
            'per_page' => 20,
            'status'   => 'approved',
        );
        $params = array_merge( $defaults, $filters );
        return $this->get( '/images?' . http_build_query( $params ) );
    }

    /**
     * Get a single image by ID.
     *
     * @return array|WP_Error
     */
    public function get_image( string $image_id ) {
        return $this->get( '/images/' . $image_id );
    }

    /**
     * Get the raw image file URL.
     */
    public function get_image_file_url( string $image_id ): string {
        return $this->api_url . '/images/' . $image_id . '/file';
    }

    /**
     * Download raw image bytes.
     *
     * @return string|WP_Error Raw bytes on success.
     */
    public function download_image( string $image_id ) {
        $url      = $this->get_image_file_url( $image_id );
        $response = wp_remote_get( $url, array(
            'timeout' => 30,
            'headers' => $this->auth_headers(),
        ) );

        if ( is_wp_error( $response ) ) {
            return $response;
        }

        $code = wp_remote_retrieve_response_code( $response );
        if ( $code !== 200 ) {
            return new \WP_Error( 'pixelvault_download_failed', "Image download failed (HTTP {$code})." );
        }

        return wp_remote_retrieve_body( $response );
    }

    // -----------------------------------------------------------------
    // Matching (auto-assign)
    // -----------------------------------------------------------------

    /**
     * Ask the backend to match images for a given post context.
     *
     * @param array $context {
     *     @type string $title       Post title.
     *     @type string $slug        Post slug.
     *     @type string $content     Post body text (first 500 chars).
     *     @type array  $categories  Category names.
     *     @type array  $tags        Tag names.
     *     @type string $focus_keyword Yoast/RankMath focus keyword (if any).
     * }
     * @return array|WP_Error Array with 'matches' key containing ranked image results.
     */
    public function match_images( array $context ) {
        $opts    = get_option( 'pixelvault_settings', array() );
        $payload = array_merge( $context, array(
            'industry'          => $opts['industry'] ?? '',
            'business_type'     => $opts['business_type'] ?? '',
            'style_prefix'      => $opts['style_prefix'] ?? '',
            'negative_keywords' => $opts['negative_keywords'] ?? '',
            'mood_tags'         => $opts['mood_tags'] ?? array(),
        ) );

        return $this->post( '/match', $payload );
    }

    // -----------------------------------------------------------------
    // Generation
    // -----------------------------------------------------------------

    /**
     * Generate images from a prompt.
     *
     * @param string $prompt  The generation prompt.
     * @param int    $count   Number of images.
     * @param string $ratio   Aspect ratio.
     * @param string $quality 'sd' or 'hq'.
     * @return array|WP_Error
     */
    public function generate( string $prompt, int $count = 1, string $ratio = '16:9', string $quality = 'sd' ) {
        return $this->post( '/generate', array(
            'prompt'  => $prompt,
            'count'   => $count,
            'ratio'   => $ratio,
            'quality' => $quality,
        ) );
    }

    // -----------------------------------------------------------------
    // Site profile
    // -----------------------------------------------------------------

    /**
     * Sync the local site profile to the backend.
     *
     * @return array|WP_Error
     */
    public function sync_site_profile() {
        $opts = get_option( 'pixelvault_settings', array() );
        return $this->post( '/sites/profile', array(
            'url'               => home_url(),
            'name'              => get_bloginfo( 'name' ),
            'industry'          => $opts['industry'] ?? '',
            'business_type'     => $opts['business_type'] ?? '',
            'location'          => $opts['location'] ?? '',
            'mood_tags'         => $opts['mood_tags'] ?? array(),
            'style_prefix'      => $opts['style_prefix'] ?? '',
            'negative_keywords' => $opts['negative_keywords'] ?? '',
        ) );
    }

    // -----------------------------------------------------------------
    // Anti-duplicate
    // -----------------------------------------------------------------

    /**
     * Check if an image is already deployed on another site in this account.
     *
     * @return array|WP_Error Array with 'deployed_on' sites list.
     */
    public function check_duplicate( string $image_id ) {
        return $this->get( '/images/' . $image_id . '/deployments' );
    }

    /**
     * Record a deployment.
     *
     * @return array|WP_Error
     */
    public function record_deployment( string $image_id, array $data ) {
        return $this->post( '/images/' . $image_id . '/deploy', $data );
    }

    // -----------------------------------------------------------------
    // HTTP internals
    // -----------------------------------------------------------------

    /**
     * @return array|WP_Error Decoded JSON body or WP_Error.
     */
    private function get( string $endpoint ) {
        $response = wp_remote_get( $this->api_url . $endpoint, array(
            'timeout' => 15,
            'headers' => $this->auth_headers(),
        ) );

        return $this->parse_response( $response );
    }

    /**
     * @return array|WP_Error Decoded JSON body or WP_Error.
     */
    private function post( string $endpoint, array $body = array() ) {
        $response = wp_remote_post( $this->api_url . $endpoint, array(
            'timeout' => 60,
            'headers' => array_merge( $this->auth_headers(), array(
                'Content-Type' => 'application/json',
            ) ),
            'body'    => wp_json_encode( $body ),
        ) );

        return $this->parse_response( $response );
    }

    /**
     * Build authorization headers.
     */
    private function auth_headers(): array {
        if ( empty( $this->api_key ) ) {
            return array();
        }
        return array(
            'X-API-Key' => $this->api_key,
        );
    }

    /**
     * Parse a wp_remote_* response into an array or WP_Error.
     *
     * @param array|WP_Error $response Raw response.
     * @return array|WP_Error
     */
    private function parse_response( $response ) {
        if ( is_wp_error( $response ) ) {
            return $response;
        }

        $code = wp_remote_retrieve_response_code( $response );
        $body = wp_remote_retrieve_body( $response );
        $data = json_decode( $body, true );

        if ( $code >= 400 ) {
            $message = $data['detail'] ?? "API error (HTTP {$code})";
            return new \WP_Error( 'pixelvault_api_error', $message, array( 'status' => $code ) );
        }

        return $data ?? array();
    }
}
