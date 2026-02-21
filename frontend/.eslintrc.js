/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  extends: ['next/core-web-vitals', 'plugin:jsx-a11y/recommended'],
  plugins: ['jsx-a11y'],
  rules: {
    // Disabled: eslint-plugin-jsx-a11y v6.10.x has a minimatch crash
    // (0 , _minimatch.default) is not a function
    // Re-enable after upgrading to jsx-a11y >=6.11
    'jsx-a11y/label-has-associated-control': 'off',
  },
};
