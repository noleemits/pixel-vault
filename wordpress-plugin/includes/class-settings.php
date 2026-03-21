<?php

namespace PixelVault;

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Settings page: Settings → PixelVault.
 *
 * Uses the WordPress Settings API for all fields.
 */
class Settings {

    private const OPTION_GROUP = 'pixelvault_settings_group';
    private const OPTION_NAME  = 'pixelvault_settings';
    private const PAGE_SLUG    = 'pixelvault';

    private const INDUSTRIES = array(
        ''              => '— Select —',
        'healthcare'    => 'Healthcare',
        'real_estate'   => 'Real Estate',
        'food'          => 'Food & Restaurant',
        'legal_finance' => 'Legal & Finance',
        'fitness'       => 'Fitness & Wellness',
        'ecommerce'     => 'E-commerce',
    );

    private const MOOD_OPTIONS = array(
        'warm'       => 'Warm',
        'friendly'   => 'Friendly',
        'clinical'   => 'Clinical',
        'luxury'     => 'Luxury',
        'energetic'  => 'Energetic',
        'minimal'    => 'Minimal',
        'bold'       => 'Bold',
        'calm'       => 'Calm',
        'playful'    => 'Playful',
        'corporate'  => 'Corporate',
    );

    private API_Client $api;

    public function __construct( API_Client $api ) {
        $this->api = $api;
    }

    /**
     * Hook into WordPress admin.
     */
    public function register(): void {
        add_action( 'admin_menu', array( $this, 'add_menu_page' ) );
        add_action( 'admin_init', array( $this, 'register_settings' ) );
    }

    /**
     * Add settings page under Settings menu.
     */
    public function add_menu_page(): void {
        add_options_page(
            __( 'PixelVault Settings', 'pixelvault' ),
            __( 'PixelVault', 'pixelvault' ),
            'manage_options',
            self::PAGE_SLUG,
            array( $this, 'render_page' )
        );
    }

    /**
     * Register all settings fields.
     */
    public function register_settings(): void {
        register_setting( self::OPTION_GROUP, self::OPTION_NAME, array(
            'type'              => 'array',
            'sanitize_callback' => array( $this, 'sanitize' ),
        ) );

        // --- Section: Connection ---
        add_settings_section( 'pv_connection', __( 'Connection', 'pixelvault' ), '__return_null', self::PAGE_SLUG );

        add_settings_field( 'api_url', __( 'API URL', 'pixelvault' ), array( $this, 'field_text' ), self::PAGE_SLUG, 'pv_connection', array(
            'field'       => 'api_url',
            'placeholder' => 'http://localhost:8000/api/v1',
            'description' => __( 'Your PixelVault backend URL.', 'pixelvault' ),
        ) );

        add_settings_field( 'api_key', __( 'API Key', 'pixelvault' ), array( $this, 'field_password' ), self::PAGE_SLUG, 'pv_connection', array(
            'field'       => 'api_key',
            'description' => __( 'Get your API key from the PixelVault dashboard.', 'pixelvault' ),
        ) );

        // --- Section: Business Profile ---
        add_settings_section( 'pv_profile', __( 'Business Profile', 'pixelvault' ), array( $this, 'section_profile' ), self::PAGE_SLUG );

        add_settings_field( 'industry', __( 'Industry', 'pixelvault' ), array( $this, 'field_select' ), self::PAGE_SLUG, 'pv_profile', array(
            'field'   => 'industry',
            'options' => self::INDUSTRIES,
        ) );

        add_settings_field( 'business_type', __( 'Business Type', 'pixelvault' ), array( $this, 'field_text' ), self::PAGE_SLUG, 'pv_profile', array(
            'field'       => 'business_type',
            'placeholder' => 'e.g. Pediatric Dental Clinic, CrossFit Gym, Italian Restaurant',
            'description' => __( 'Be specific — this shapes every image generated for your site.', 'pixelvault' ),
        ) );

        add_settings_field( 'location', __( 'Location', 'pixelvault' ), array( $this, 'field_text' ), self::PAGE_SLUG, 'pv_profile', array(
            'field'       => 'location',
            'placeholder' => 'e.g. Miami, FL',
            'description' => __( 'Optional. Adds local context to generated images.', 'pixelvault' ),
        ) );

        // --- Section: Visual Style ---
        add_settings_section( 'pv_style', __( 'Visual Style', 'pixelvault' ), array( $this, 'section_style' ), self::PAGE_SLUG );

        add_settings_field( 'mood_tags', __( 'Mood / Tone', 'pixelvault' ), array( $this, 'field_checkboxes' ), self::PAGE_SLUG, 'pv_style', array(
            'field'   => 'mood_tags',
            'options' => self::MOOD_OPTIONS,
        ) );

        add_settings_field( 'style_prefix', __( 'Style Prefix', 'pixelvault' ), array( $this, 'field_textarea' ), self::PAGE_SLUG, 'pv_style', array(
            'field'       => 'style_prefix',
            'placeholder' => 'e.g. soft natural lighting, warm color palette, pastel accents, modern clean interior',
            'description' => __( 'Added to every prompt. Describe the visual feel you want across all images.', 'pixelvault' ),
            'rows'        => 3,
        ) );

        add_settings_field( 'negative_keywords', __( 'Negative Keywords', 'pixelvault' ), array( $this, 'field_textarea' ), self::PAGE_SLUG, 'pv_style', array(
            'field'       => 'negative_keywords',
            'placeholder' => 'e.g. dark moody lighting, clinical sterile look, scary tools, needles',
            'description' => __( 'Things to avoid in all images. Comma-separated.', 'pixelvault' ),
            'rows'        => 2,
        ) );

        // --- Section: Behavior ---
        add_settings_section( 'pv_behavior', __( 'Behavior', 'pixelvault' ), '__return_null', self::PAGE_SLUG );

        add_settings_field( 'auto_assign', __( 'Auto-assign featured image', 'pixelvault' ), array( $this, 'field_toggle' ), self::PAGE_SLUG, 'pv_behavior', array(
            'field'       => 'auto_assign',
            'description' => __( 'Automatically find and set a featured image when saving a post.', 'pixelvault' ),
        ) );

        add_settings_field( 'auto_body', __( 'Suggest body images', 'pixelvault' ), array( $this, 'field_toggle' ), self::PAGE_SLUG, 'pv_behavior', array(
            'field'       => 'auto_body',
            'description' => __( 'Suggest images for sections within the post body.', 'pixelvault' ),
        ) );

        add_settings_field( 'quality', __( 'Default quality', 'pixelvault' ), array( $this, 'field_select' ), self::PAGE_SLUG, 'pv_behavior', array(
            'field'   => 'quality',
            'options' => array(
                'sd' => 'SD — Standard (~1400px)',
                'hq' => 'HQ — High Quality (2500px+) — extra cost',
            ),
        ) );

        add_settings_field( 'serving_mode', __( 'Image serving', 'pixelvault' ), array( $this, 'field_select' ), self::PAGE_SLUG, 'pv_behavior', array(
            'field'   => 'serving_mode',
            'options' => array(
                'cdn'   => 'CDN — Serve from PixelVault (fast, recommended)',
                'local' => 'Local — Download to wp-content/uploads',
            ),
        ) );
    }

    // -----------------------------------------------------------------
    // Field renderers
    // -----------------------------------------------------------------

    public function field_text( array $args ): void {
        $opts  = get_option( self::OPTION_NAME, array() );
        $value = esc_attr( $opts[ $args['field'] ] ?? '' );
        printf(
            '<input type="text" name="%s[%s]" value="%s" class="regular-text" placeholder="%s">',
            self::OPTION_NAME,
            esc_attr( $args['field'] ),
            $value,
            esc_attr( $args['placeholder'] ?? '' )
        );
        if ( ! empty( $args['description'] ) ) {
            printf( '<p class="description">%s</p>', esc_html( $args['description'] ) );
        }
    }

    public function field_password( array $args ): void {
        $opts  = get_option( self::OPTION_NAME, array() );
        $value = $opts[ $args['field'] ] ?? '';
        $masked = ! empty( $value ) ? str_repeat( '•', 12 ) . substr( $value, -4 ) : '';
        printf(
            '<input type="password" name="%s[%s]" value="%s" class="regular-text" autocomplete="new-password">',
            self::OPTION_NAME,
            esc_attr( $args['field'] ),
            esc_attr( $value )
        );
        if ( ! empty( $args['description'] ) ) {
            printf( '<p class="description">%s</p>', esc_html( $args['description'] ) );
        }
    }

    public function field_select( array $args ): void {
        $opts    = get_option( self::OPTION_NAME, array() );
        $current = $opts[ $args['field'] ] ?? '';
        printf( '<select name="%s[%s]">', self::OPTION_NAME, esc_attr( $args['field'] ) );
        foreach ( $args['options'] as $val => $label ) {
            printf(
                '<option value="%s" %s>%s</option>',
                esc_attr( $val ),
                selected( $current, $val, false ),
                esc_html( $label )
            );
        }
        echo '</select>';
    }

    public function field_textarea( array $args ): void {
        $opts  = get_option( self::OPTION_NAME, array() );
        $value = esc_textarea( $opts[ $args['field'] ] ?? '' );
        printf(
            '<textarea name="%s[%s]" class="large-text" rows="%d" placeholder="%s">%s</textarea>',
            self::OPTION_NAME,
            esc_attr( $args['field'] ),
            (int) ( $args['rows'] ?? 3 ),
            esc_attr( $args['placeholder'] ?? '' ),
            $value
        );
        if ( ! empty( $args['description'] ) ) {
            printf( '<p class="description">%s</p>', esc_html( $args['description'] ) );
        }
    }

    public function field_checkboxes( array $args ): void {
        $opts     = get_option( self::OPTION_NAME, array() );
        $selected = (array) ( $opts[ $args['field'] ] ?? array() );
        echo '<fieldset>';
        foreach ( $args['options'] as $val => $label ) {
            printf(
                '<label style="margin-right:16px;"><input type="checkbox" name="%s[%s][]" value="%s" %s> %s</label>',
                self::OPTION_NAME,
                esc_attr( $args['field'] ),
                esc_attr( $val ),
                checked( in_array( $val, $selected, true ), true, false ),
                esc_html( $label )
            );
        }
        echo '</fieldset>';
    }

    public function field_toggle( array $args ): void {
        $opts  = get_option( self::OPTION_NAME, array() );
        $value = (bool) ( $opts[ $args['field'] ] ?? false );
        printf(
            '<label><input type="checkbox" name="%s[%s]" value="1" %s> %s</label>',
            self::OPTION_NAME,
            esc_attr( $args['field'] ),
            checked( $value, true, false ),
            esc_html( $args['description'] ?? '' )
        );
    }

    // -----------------------------------------------------------------
    // Section descriptions
    // -----------------------------------------------------------------

    public function section_profile(): void {
        echo '<p>' . esc_html__( 'Tell PixelVault about your business so every image matches your brand.', 'pixelvault' ) . '</p>';
    }

    public function section_style(): void {
        echo '<p>' . esc_html__( 'Define the visual tone for all images on this site. These settings are injected into every generation prompt.', 'pixelvault' ) . '</p>';
    }

    // -----------------------------------------------------------------
    // Sanitization
    // -----------------------------------------------------------------

    public function sanitize( $input ): array {
        $old  = get_option( self::OPTION_NAME, array() );
        $safe = array();

        $safe['api_url']           = esc_url_raw( $input['api_url'] ?? $old['api_url'] ?? 'http://localhost:8000/api/v1' );
        $safe['api_key']           = sanitize_text_field( $input['api_key'] ?? $old['api_key'] ?? '' );
        $safe['industry']          = sanitize_text_field( $input['industry'] ?? '' );
        $safe['business_type']     = sanitize_text_field( $input['business_type'] ?? '' );
        $safe['location']          = sanitize_text_field( $input['location'] ?? '' );
        $safe['mood_tags']         = array_map( 'sanitize_text_field', (array) ( $input['mood_tags'] ?? array() ) );
        $safe['style_prefix']      = sanitize_textarea_field( $input['style_prefix'] ?? '' );
        $safe['negative_keywords'] = sanitize_textarea_field( $input['negative_keywords'] ?? '' );
        $safe['auto_assign']       = ! empty( $input['auto_assign'] );
        $safe['auto_body']         = ! empty( $input['auto_body'] );
        $safe['quality']           = in_array( $input['quality'] ?? 'sd', array( 'sd', 'hq' ), true ) ? $input['quality'] : 'sd';
        $safe['serving_mode']      = in_array( $input['serving_mode'] ?? 'cdn', array( 'cdn', 'local' ), true ) ? $input['serving_mode'] : 'cdn';

        // Sync profile to backend after save.
        if ( ! empty( $safe['api_key'] ) ) {
            $this->api->sync_site_profile();
        }

        return $safe;
    }

    // -----------------------------------------------------------------
    // Page render
    // -----------------------------------------------------------------

    public function render_page(): void {
        if ( ! current_user_can( 'manage_options' ) ) {
            return;
        }
        ?>
        <div class="wrap">
            <h1><?php esc_html_e( 'PixelVault Settings', 'pixelvault' ); ?></h1>

            <?php if ( $this->api->is_connected() ) : ?>
                <div id="pv-connection-status" class="notice notice-info">
                    <p><?php esc_html_e( 'Testing connection...', 'pixelvault' ); ?></p>
                </div>
                <script>
                    document.addEventListener('DOMContentLoaded', function() {
                        fetch(pixelvaultAdmin.restUrl + 'connection-test', {
                            headers: { 'X-WP-Nonce': pixelvaultAdmin.nonce }
                        })
                        .then(r => r.json())
                        .then(data => {
                            const el = document.getElementById('pv-connection-status');
                            el.className = data.ok ? 'notice notice-success' : 'notice notice-error';
                            el.querySelector('p').textContent = data.message;
                        })
                        .catch(() => {
                            const el = document.getElementById('pv-connection-status');
                            el.className = 'notice notice-error';
                            el.querySelector('p').textContent = 'Could not reach PixelVault backend.';
                        });
                    });
                </script>
            <?php endif; ?>

            <form method="post" action="options.php">
                <?php
                settings_fields( self::OPTION_GROUP );
                do_settings_sections( self::PAGE_SLUG );
                submit_button( __( 'Save Settings', 'pixelvault' ) );
                ?>
            </form>

            <?php if ( $this->api->is_connected() ) : ?>
                <hr>
                <h2><?php esc_html_e( 'Preview Style', 'pixelvault' ); ?></h2>
                <p><?php esc_html_e( 'Generate 2 sample images using your current style profile to see how your images will look.', 'pixelvault' ); ?></p>
                <button type="button" class="button button-secondary" id="pv-preview-style">
                    <?php esc_html_e( 'Generate Preview', 'pixelvault' ); ?>
                </button>
                <div id="pv-preview-grid" style="display:flex;gap:12px;margin-top:12px;"></div>
            <?php endif; ?>
        </div>
        <?php
    }
}
