<?php
/**
 * Plugin Name:       PixelVault
 * Plugin URI:        https://pixelvault.io
 * Description:       AI-powered image bank for WordPress. Auto-assigns branded images, prevents duplicates across client sites, and generates on demand.
 * Version:           0.1.0
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

define( 'PIXELVAULT_VERSION', '0.1.0' );
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
            'api_url'           => 'http://localhost:8000/api/v1',
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
 * Boot the plugin.
 */
function pixelvault_init() {
    $plugin = new PixelVault\Plugin();
    $plugin->init();
}
add_action( 'plugins_loaded', 'pixelvault_init' );
