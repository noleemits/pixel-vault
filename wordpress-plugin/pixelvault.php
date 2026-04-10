<?php
/**
 * Plugin Name:       PixelVault
 * Plugin URI:        https://pixelvault.io
 * Description:       AI-powered image bank for WordPress. Auto-assigns branded images, prevents duplicates across client sites, and generates on demand.
 * Version:           0.2.1
 * Author:            Noleemits
 * Author URI:        https://noleemits.com
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       pixelvault
 * Domain Path:       /languages
 * Requires at least: 6.0
 * Requires PHP:      8.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

define( 'PIXELVAULT_VERSION', '0.2.1' );
define( 'PIXELVAULT_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'PIXELVAULT_PLUGIN_URL', plugin_dir_url( __FILE__ ) );
define( 'PIXELVAULT_PLUGIN_BASENAME', plugin_basename( __FILE__ ) );

/**
 * Autoloader for plugin classes.
 */
spl_autoload_register( function ( $class ) {
    $prefix = 'PixelVault\\';
    if ( strncmp( $prefix, $class, strlen( $prefix ) ) !== 0 ) {
        return;
    }

    $relative_class = substr( $class, strlen( $prefix ) );
    $file = PIXELVAULT_PLUGIN_DIR . 'includes/class-' . strtolower( str_replace( '_', '-', $relative_class ) ) . '.php';

    if ( file_exists( $file ) ) {
        require $file;
    }
});

/**
 * Plugin activation.
 */
function pixelvault_activate() {
    // Set default options on first activation.
    if ( false === get_option( 'pixelvault_settings' ) ) {
        update_option( 'pixelvault_settings', array(
            'api_key'           => '',
            'api_url'           => 'https://vaultapi.noleemits.com/api/v1',
            'industry'          => '',
            'business_type'     => '',
            'location'          => '',
            'mood_tags'         => array(),
            'style_prefix'      => '',
            'negative_keywords' => '',
            'serving_mode'      => 'cdn',
            'auto_assign'       => true,
            'auto_featured'     => true,
            'auto_body'         => false,
            'quality'           => 'sd',
        ) );
    }
    flush_rewrite_rules();
}
register_activation_hook( __FILE__, 'pixelvault_activate' );

/**
 * Plugin deactivation.
 */
function pixelvault_deactivate() {
    flush_rewrite_rules();
}
register_deactivation_hook( __FILE__, 'pixelvault_deactivate' );

/**
 * Freemius SDK integration.
 *
 * Handles licensing, checkout, and subscription management.
 * SDK directory must exist at pixelvault/freemius/start.php
 */
if ( ! function_exists( 'pv_fs' ) ) {
    function pv_fs() {
        global $pv_fs;
        if ( ! isset( $pv_fs ) ) {
            if ( ! defined( 'WP_FS__PRODUCT_27379_MULTISITE' ) ) {
                define( 'WP_FS__PRODUCT_27379_MULTISITE', true );
            }

            // Only load if Freemius SDK is present.
            $fs_start = dirname( __FILE__ ) . '/freemius/start.php';
            if ( ! file_exists( $fs_start ) ) {
                return null;
            }

            require_once $fs_start;
            $pv_fs = fs_dynamic_init( array(
                'id'                  => '27379',
                'slug'                => 'pixelvault',
                'type'                => 'plugin',
                'public_key'          => 'pk_cb98febf4e14fdf664e591ac672d9', 
                'has_premium_version' => true,
                'has_addons'          => true,
                'has_paid_plans'      => true,
                'menu'                => array(
                    'slug'   => 'pixelvault',
                    'parent' => array( 'slug' => 'options-general.php' ),
                ),
            ) );
        }
        return $pv_fs;
    }
    pv_fs();
    do_action( 'pv_fs_loaded' );
}

/**
 * On Freemius opt-in (free or paid), register with our backend and store API key.
 */
function pv_fs_after_activation() {
    $fs = pv_fs();
    if ( ! $fs ) {
        return;
    }

    $user = $fs->get_user();
    if ( ! $user ) {
        return;
    }

    $opts = get_option( 'pixelvault_settings', array() );

    // Don't re-register if already have an API key.
    if ( ! empty( $opts['api_key'] ) ) {
        return;
    }

    $api_url = untrailingslashit( $opts['api_url'] ?? 'https://vaultapi.noleemits.com/api/v1' );

    $license = $fs->_get_license();

    $response = wp_remote_post( $api_url . '/accounts/register', array(
        'timeout' => 15,
        'headers' => array( 'Content-Type' => 'application/json' ),
        'body'    => wp_json_encode( array(
            'email'            => $user->email,
            'name'             => trim( $user->first . ' ' . $user->last ),
            'freemius_user_id' => $user->id,
            'license_key'      => $license ? $license->secret_key : null,
        ) ),
    ) );

    if ( is_wp_error( $response ) ) {
        return;
    }

    $body = json_decode( wp_remote_retrieve_body( $response ), true );

    if ( ! empty( $body['api_key'] ) ) {
        $opts['api_key'] = sanitize_text_field( $body['api_key'] );
        update_option( 'pixelvault_settings', $opts );
    }
}

// Hook into Freemius activation — only if SDK loaded.
if ( function_exists( 'pv_fs' ) && pv_fs() ) {
    pv_fs()->add_action( 'after_account_connection', 'pv_fs_after_activation' );
}

/**
 * Boot the plugin.
 */
function pixelvault_init() {
    $plugin = new PixelVault\Plugin();
    $plugin->init();
}
add_action( 'plugins_loaded', 'pixelvault_init' );
