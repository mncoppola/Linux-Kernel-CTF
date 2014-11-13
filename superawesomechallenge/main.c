#include <linux/module.h>
#include <linux/kernel.h>

static int __init init_superawesomechallenge ( void )
{
    return 0;
}

static void __exit exit_superawesomechallenge ( void )
{
}

module_init(init_superawesomechallenge);
module_exit(exit_superawesomechallenge);

MODULE_LICENSE("GPL");
