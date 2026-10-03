-- Catppuccin, flavoured after 'background': Frappé when dark, like starship, tmux and gitui.
return {
  "catppuccin/nvim",
  priority = 1000,
  config = function()
    require("catppuccin").setup({
      flavour = "auto",
      background = { light = "latte", dark = "frappe" },
      transparent_background = true,
      term_colors = true,
      integrations = {
        cmp = true,
        gitsigns = true,
        mason = true,
        noice = true,
        nvimtree = true,
        telescope = true,
        treesitter = true,
        which_key = true,
      },
    })
    vim.cmd.colorscheme("catppuccin")
  end,
}
