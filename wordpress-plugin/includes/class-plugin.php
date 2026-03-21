<?php

namespace PixelVault;

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

/**
 * Core plugin orchestrator.
 */
class Plugin {

    /** @var API_Client */
    private API_Client $api;

    /** @var Settings */
    private Settings $settings;

    /** @var Rest_API */
    private Rest_API $rest;

    /** @var Image_Handler */
    private Image_Handler $image_handler;

    /** @var Auto_Assign */
    private Auto_Assign $auto_assign;

    /** @var Notification */
    private Notification $notification;

    /**
     * Wire everything together.
     */
    public function init(): void {
        $this->api           = new API_Client();
        $this->image_handler = new Image_Handler( $this->api );
        $this->auto_assign   = new Auto_Assign( $this->api, $this->image_handler );
        $this->notification  = new Notification();
        $this->settings      = new Settings( $this->api );
        $this->rest          = new Rest_API( $this->api, $this->image_handler, $this->auto_assign );

        // Admin hooks.
        if ( is_admin() ) {
            $this->settings->register();
            $this->notification->register();
            add_action( 'admin_enqueue_scripts', array( $this, 'enqueue_admin_assets' ) );
            add_filter( 'plugin_action_links_' . PIXELVAULT_PLUGIN_BASENAME, array( $this, 'add_settings_link' ) );
        }

        // REST API — always active (AJAX calls from editor).
        add_action( 'rest_api_init', array( $this->rest, 'register_routes' ) );

        // Gutenberg sidebar.
        add_action( 'enqueue_block_editor_assets', array( $this, 'enqueue_editor_assets' ) );

        // Auto-assign on save.
        add_action( 'save_post', array( $this->auto_assign, 'on_save_post' ), 20, 3 );
    }

    /**
     * Enqueue admin-wide assets (settings page, notifications).
     */
    public function enqueue_admin_assets( string $hook ): void {
        // Notification toast — on all admin pages.
        wp_enqueue_style(
            'pixelvault-admin',
            PIXELVAULT_PLUGIN_URL . 'assets/css/admin.css',
            array(),
            PIXELVAULT_VERSION
        );
        wp_enqueue_script(
            'pixelvault-admin',
            PIXELVAULT_PLUGIN_URL . 'assets/js/admin.js',
            array(),
            PIXELVAULT_VERSION,
            true
        );
        wp_localize_script( 'pixelvault-admin', 'pixelvaultAdmin', array(
            'restUrl'  => rest_url( 'pixelvault/v1/' ),
            'nonce'    => wp_create_nonce( 'wp_rest' ),
            'settings' => $this->get_safe_settings(),
        ) );
    }

    /**
     * Enqueue Gutenberg editor sidebar.
     */
    public function enqueue_editor_assets(): void {
        $build_path = PIXELVAULT_PLUGIN_DIR . 'blocks/pixelvault-sidebar/build/';

        if ( file_exists( $build_path . 'index.js' ) ) {
            $asset = file_exists( $build_path . 'index.asset.php' )
                ? require $build_path . 'index.asset.php'
                : array( 'dependencies' => array(), 'version' => PIXELVAULT_VERSION );

            wp_enqueue_script(
                'pixelvault-sidebar',
                PIXELVAULT_PLUGIN_URL . 'blocks/pixelvault-sidebar/build/index.js',
                $asset['dependencies'],
                $asset['version'],
                true
            );

            wp_localize_script( 'pixelvault-sidebar', 'pixelvaultEditor', array(
                'restUrl'  => rest_url( 'pixelvault/v1/' ),
                'nonce'    => wp_create_nonce( 'wp_rest' ),
                'settings' => $this->get_safe_settings(),
            ) );
        }

        if ( file_exists( $build_path . 'index.css' ) ) {
            wp_enqueue_style(
                'pixelvault-sidebar',
                PIXELVAULT_PLUGIN_URL . 'blocks/pixelvault-sidebar/build/index.css',
                array(),
                PIXELVAULT_VERSION
            );
        }
    }

    /**
     * Add "Settings" link on Plugins page.
     */
    public function add_settings_link( array $links ): array {
        $url  = admin_url( 'options-general.php?page=pixelvault' );
        $link = '<a href="' . esc_url( $url ) . '">' . esc_html__( 'Settings', 'pixelvault' ) . '</a>';
        array_unshift( $links, $link );
        return $links;
    }

    /**
     * Return settings safe for JS (no API key).
     */
    private function get_safe_settings(): array {
        $opts = get_option( 'pixelvault_settings', array() );
        return array(
            'connected'     => ! empty( $opts['api_key'] ),
            'industry'      => $opts['industry'] ?? '',
            'business_type' => $opts['business_type'] ?? '',
            'auto_assign'   => $opts['auto_assign'] ?? true,
            'quality'        => $opts['quality'] ?? 'sd',
        );
    }
}
