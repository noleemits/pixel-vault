<?php
/**
 * PixelVault uninstall — clean up all plugin data.
 */

if ( ! defined( 'WP_UNINSTALL_PLUGIN' ) ) {
    exit;
}

// Remove plugin options.
delete_option( 'pixelvault_settings' );
delete_option( 'pixelvault_site_id' );

// Remove cached images if serving locally.
$upload_dir = wp_upload_dir();
$pv_dir     = $upload_dir['basedir'] . '/pixelvault';
if ( is_dir( $pv_dir ) ) {
    $files = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator( $pv_dir, RecursiveDirectoryIterator::SKIP_DOTS ),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ( $files as $file ) {
        if ( $file->isDir() ) {
            rmdir( $file->getRealPath() );
        } else {
            unlink( $file->getRealPath() );
        }
    }
    rmdir( $pv_dir );
}
