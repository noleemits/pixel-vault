<?php

namespace PixelVault;

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Internal WP REST API endpoints.
 *
 * These are called by the Gutenberg sidebar and admin JS.
 * Namespace: pixelvault/v1
 */
class Rest_API {

    private API_Client $api;
    private Image_Handler $handler;
    private Auto_Assign $auto_assign;

    public function __construct( API_Client $api, Image_Handler $handler, Auto_Assign $auto_assign ) {
        $this->api         = $api;
        $this->handler     = $handler;
        $this->auto_assign = $auto_assign;
    }

    /**
     * Register all routes.
     */
    public function register_routes(): void {
        $namespace = 'pixelvault/v1';

        // Connection test.
        register_rest_route( $namespace, '/connection-test', array(
            'methods'             => 'GET',
            'callback'            => array( $this, 'connection_test' ),
            'permission_callback' => array( $this, 'can_manage' ),
        ) );

        // Browse images (proxy to backend).
        register_rest_route( $namespace, '/images', array(
            'methods'             => 'GET',
            'callback'            => array( $this, 'browse_images' ),
            'permission_callback' => array( $this, 'can_edit' ),
            'args'                => array(
                'industry' => array( 'type' => 'string', 'default' => '' ),
                'style'    => array( 'type' => 'string', 'default' => '' ),
                'ratio'    => array( 'type' => 'string', 'default' => '' ),
                'search'   => array( 'type' => 'string', 'default' => '' ),
                'page'     => array( 'type' => 'integer', 'default' => 1 ),
                'per_page' => array( 'type' => 'integer', 'default' => 20 ),
            ),
        ) );

        // Insert image into post.
        register_rest_route( $namespace, '/insert', array(
            'methods'             => 'POST',
            'callback'            => array( $this, 'insert_image' ),
            'permission_callback' => array( $this, 'can_edit' ),
            'args'                => array(
                'image_id'    => array( 'type' => 'string', 'required' => true ),
                'post_id'     => array( 'type' => 'integer', 'required' => true ),
                'as_featured' => array( 'type' => 'boolean', 'default' => false ),
            ),
        ) );

        // Check anti-duplicate.
        register_rest_route( $namespace, '/check-duplicate/(?P<image_id>[a-f0-9-]+)', array(
            'methods'             => 'GET',
            'callback'            => array( $this, 'check_duplicate' ),
            'permission_callback' => array( $this, 'can_edit' ),
        ) );

        // Get suggestions for a post.
        register_rest_route( $namespace, '/suggestions/(?P<post_id>\d+)', array(
            'methods'             => 'GET',
            'callback'            => array( $this, 'get_suggestions' ),
            'permission_callback' => array( $this, 'can_edit' ),
        ) );

        // Generate image from prompt.
        register_rest_route( $namespace, '/generate', array(
            'methods'             => 'POST',
            'callback'            => array( $this, 'generate_image' ),
            'permission_callback' => array( $this, 'can_edit' ),
            'args'                => array(
                'prompt'  => array( 'type' => 'string', 'required' => true ),
                'post_id' => array( 'type' => 'integer', 'required' => true ),
                'ratio'   => array( 'type' => 'string', 'default' => '16:9' ),
                'quality' => array( 'type' => 'string', 'default' => 'sd' ),
            ),
        ) );
    }

    // -----------------------------------------------------------------
    // Callbacks
    // -----------------------------------------------------------------

    public function connection_test(): \WP_REST_Response {
        return new \WP_REST_Response( $this->api->test_connection() );
    }

    public function browse_images( \WP_REST_Request $request ): \WP_REST_Response {
        $filters = array(
            'industry' => $request->get_param( 'industry' ),
            'style'    => $request->get_param( 'style' ),
            'ratio'    => $request->get_param( 'ratio' ),
            'page'     => $request->get_param( 'page' ),
            'per_page' => $request->get_param( 'per_page' ),
        );

        // Remove empty filters.
        $filters = array_filter( $filters, function ( $v ) {
            return $v !== '' && $v !== null;
        } );

        $result = $this->api->get_images( $filters );

        if ( is_wp_error( $result ) ) {
            return new \WP_REST_Response( array( 'error' => $result->get_error_message() ), 502 );
        }

        return new \WP_REST_Response( $result );
    }

    public function insert_image( \WP_REST_Request $request ): \WP_REST_Response {
        $image_id    = sanitize_text_field( $request->get_param( 'image_id' ) );
        $post_id     = (int) $request->get_param( 'post_id' );
        $as_featured = (bool) $request->get_param( 'as_featured' );

        $post = get_post( $post_id );
        if ( ! $post ) {
            return new \WP_REST_Response( array( 'error' => 'Post not found.' ), 404 );
        }

        // Build SEO context.
        $context = $this->auto_assign->extract_context( $post );
        $seo     = array(
            'title'         => $context['title'],
            'slug'          => $context['slug'],
            'focus_keyword' => $context['focus_keyword'] ?? '',
        );

        $attach_id = $this->handler->insert_image( $image_id, $post_id, $as_featured, $seo );

        if ( is_wp_error( $attach_id ) ) {
            return new \WP_REST_Response( array( 'error' => $attach_id->get_error_message() ), 500 );
        }

        return new \WP_REST_Response( array(
            'attachment_id' => $attach_id,
            'url'           => wp_get_attachment_url( $attach_id ),
            'message'       => $as_featured
                ? __( 'Featured image set.', 'pixelvault' )
                : __( 'Image inserted.', 'pixelvault' ),
        ) );
    }

    public function check_duplicate( \WP_REST_Request $request ): \WP_REST_Response {
        $image_id = sanitize_text_field( $request->get_param( 'image_id' ) );
        $result   = $this->api->check_duplicate( $image_id );

        if ( is_wp_error( $result ) ) {
            return new \WP_REST_Response( array( 'deployed_on' => array() ) );
        }

        return new \WP_REST_Response( $result );
    }

    public function get_suggestions( \WP_REST_Request $request ): \WP_REST_Response {
        $post_id = (int) $request->get_param( 'post_id' );

        // Check for stored suggestions.
        $suggestions = get_post_meta( $post_id, '_pixelvault_suggestions', true );
        $no_match    = get_post_meta( $post_id, '_pixelvault_no_match', true );
        $prompt      = get_post_meta( $post_id, '_pixelvault_suggested_prompt', true );

        return new \WP_REST_Response( array(
            'suggestions'      => $suggestions ? json_decode( $suggestions, true ) : array(),
            'no_match'         => (bool) $no_match,
            'suggested_prompt' => $prompt ?: null,
        ) );
    }

    public function generate_image( \WP_REST_Request $request ): \WP_REST_Response {
        $prompt  = sanitize_text_field( $request->get_param( 'prompt' ) );
        $post_id = (int) $request->get_param( 'post_id' );
        $ratio   = sanitize_text_field( $request->get_param( 'ratio' ) );
        $quality = sanitize_text_field( $request->get_param( 'quality' ) );

        $result = $this->api->generate( $prompt, 1, $ratio, $quality );

        if ( is_wp_error( $result ) ) {
            return new \WP_REST_Response( array( 'error' => $result->get_error_message() ), 500 );
        }

        return new \WP_REST_Response( array(
            'batch_id' => $result['batch_id'] ?? null,
            'status'   => 'generating',
            'message'  => __( 'Image is being generated. You will be notified when ready.', 'pixelvault' ),
        ) );
    }

    // -----------------------------------------------------------------
    // Permission callbacks
    // -----------------------------------------------------------------

    public function can_manage(): bool {
        return current_user_can( 'manage_options' );
    }

    public function can_edit(): bool {
        return current_user_can( 'edit_posts' );
    }
}
