<?php
/**
 * PixelVault Bridge — Drop-in class for WordPress plugins.
 *
 * Usage in any WP plugin:
 *   require_once 'class-pixelvault-bridge.php';
 *   $pv = new PixelVault_Bridge('https://your-server.com', 'your-api-key');
 *   $images = $pv->get_images(['industry' => 'healthcare', 'status' => 'approved']);
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class PixelVault_Bridge {

    private string $api_url;
    private string $api_key;
    private int $cache_ttl;

    public function __construct( string $api_url, string $api_key, int $cache_ttl = 300 ) {
        $this->api_url   = rtrim( $api_url, '/' );
        $this->api_key   = $api_key;
        $this->cache_ttl = $cache_ttl;
    }

    public function get_images( array $filters = [] ) {
        $cache_key = 'pv_images_' . md5( wp_json_encode( $filters ) );
        $cached    = get_transient( $cache_key );
        if ( false !== $cached ) {
            return $cached;
        }
        $result = $this->request( 'GET', '/api/v1/images', $filters );
        if ( ! is_wp_error( $result ) ) {
            set_transient( $cache_key, $result, $this->cache_ttl );
        }
        return $result;
    }

    public function get_image( int $image_id ) {
        return $this->request( 'GET', "/api/v1/images/{$image_id}" );
    }

    public function get_image_url( int $image_id ): string {
        return $this->api_url . "/api/v1/images/{$image_id}/file";
    }

    public function review_image( int $image_id, string $status, ?int $quality_score = null ) {
        $body = [ 'status' => $status ];
        if ( null !== $quality_score ) {
            $body['quality_score'] = $quality_score;
        }
        return $this->request( 'PATCH', "/api/v1/images/{$image_id}/review", [], $body );
    }

    public function get_prompts( ?string $industry = null ) {
        $params = $industry ? [ 'industry' => $industry ] : [];
        return $this->request( 'GET', '/api/v1/prompts', $params );
    }

    public function update_prompt( int $prompt_id, array $fields ) {
        return $this->request( 'PATCH', "/api/v1/prompts/{$prompt_id}", [], $fields );
    }

    public function generate_batch( int $prompt_id, int $count = 4, string $ratio = '16:9' ) {
        return $this->request( 'POST', '/api/v1/generate', [], [
            'prompt_id' => $prompt_id,
            'count'     => $count,
            'ratio'     => $ratio,
        ] );
    }

    public function get_batch( int $batch_id ) {
        return $this->request( 'GET', "/api/v1/batches/{$batch_id}" );
    }

    public function get_batches( ?string $status = null ) {
        $params = $status ? [ 'status' => $status ] : [];
        return $this->request( 'GET', '/api/v1/batches', $params );
    }

    public function add_tag( int $image_id, string $tag_name ) {
        return $this->request( 'POST', "/api/v1/images/{$image_id}/tags/{$tag_name}" );
    }

    public function remove_tag( int $image_id, string $tag_name ) {
        return $this->request( 'DELETE', "/api/v1/images/{$image_id}/tags/{$tag_name}" );
    }

    public function get_stats() {
        return $this->request( 'GET', '/api/v1/stats' );
    }

    private function request( string $method, string $endpoint, array $query = [], array $body = [] ) {
        $url = $this->api_url . $endpoint;
        if ( ! empty( $query ) ) {
            $url = add_query_arg( $query, $url );
        }

        $args = [
            'method'  => $method,
            'headers' => [
                'X-API-Key'    => $this->api_key,
                'Content-Type' => 'application/json',
                'Accept'       => 'application/json',
            ],
            'timeout' => 30,
        ];

        if ( ! empty( $body ) ) {
            $args['body'] = wp_json_encode( $body );
        }

        $response = wp_remote_request( $url, $args );

        if ( is_wp_error( $response ) ) {
            return $response;
        }

        $code = wp_remote_retrieve_response_code( $response );
        $data = json_decode( wp_remote_retrieve_body( $response ), true );

        if ( $code >= 400 ) {
            return new \WP_Error(
                'pixelvault_api_error',
                $data['detail'] ?? "API error: HTTP {$code}",
                [ 'status' => $code ]
            );
        }

        return $data;
    }
}
