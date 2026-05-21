// Variables
const { src, dest, watch, parallel } = require('gulp');
const browserSync = require('browser-sync').create();
const concat = require('gulp-concat');
const terser = require('gulp-terser');
const cleanCSS = require('gulp-clean-css');
const sourcemaps = require('gulp-sourcemaps');
const dartSass = require('gulp-dart-sass');
const header = require('gulp-header'); // keep if you use it elsewhere

// Compile main SASS
function sassTask() {
  return src('sass/style.scss')
    .pipe(sourcemaps.init())
    .pipe(dartSass().on('error', dartSass.logError))
    .pipe(dest('css')) // concatinated css file
    .pipe(concat('style.min.css'))
    .pipe(cleanCSS({ level: 2 }))
    .pipe(sourcemaps.write('.'))
    .pipe(dest('css'))
    .pipe(browserSync.stream());
}

// Compile responsive SASS
function responsiveTask() {
  return src('sass/responsive.scss')
    .pipe(sourcemaps.init())
    .pipe(dartSass().on('error', dartSass.logError))
    .pipe(dest('css')) // concatinated css file
    .pipe(concat('responsive.min.css'))
    .pipe(cleanCSS({ level: 2 }))
    .pipe(sourcemaps.write('.'))
    .pipe(dest('css'))
    .pipe(browserSync.stream());
}

// Compile icons
function iconTask() {
  return src('sass/icon/icon.scss')
    .pipe(sourcemaps.init())
    .pipe(dartSass().on('error', dartSass.logError))
    .pipe(dest('css')) // concatinated css file
    .pipe(concat('icon.min.css'))
    .pipe(cleanCSS({ level: 2 }))
    .pipe(sourcemaps.write('.'))
    .pipe(dest('css'))
    .pipe(browserSync.stream());
}

// Compile vendor styles
function vendorsTask() {
  return src('sass/vendors/**/*.scss')
    .pipe(sourcemaps.init())
    .pipe(dartSass().on('error', dartSass.logError))
    .pipe(dest('css')) // concatinated css file
    .pipe(concat('vendors.min.css'))
    .pipe(cleanCSS({ level: 2 }))
    .pipe(sourcemaps.write('.'))
    .pipe(dest('css'))
    .pipe(browserSync.stream());
}

// Concat + minify vendor JS
function concatVendorsTask() {
  return src('js/vendors/*.js')
    .pipe(concat('vendors.min.js'))
    .pipe(terser({ output: { comments: /^!/ } }))
    .pipe(dest('js'))
    .pipe(browserSync.stream());
}

// BrowserSync
function browserSyncTask() {
  browserSync.init({
    watch: true,
    online: true,
    server: { baseDir: './' }
  });
}

// Watch files
function watchTask() {
  watch('sass/**/*.scss', sassTask);
  watch('sass/icon/*.scss', iconTask);
  watch('sass/vendors/**/*.scss', vendorsTask);
  watch(['sass/theme-responsive/**/*.scss', 'sass/responsive.scss'], responsiveTask);
  watch('js/vendors/*.js', concatVendorsTask);
}

// Default task
exports.default = parallel(
  browserSyncTask,
  sassTask,
  iconTask,
  vendorsTask,
  concatVendorsTask,
  responsiveTask,
  watchTask
);
