#include "socket_manager.h"
#include "sign.h"


int main() {
    // Create sign instance
    Sign sign = Sign::create();
    sign.Initialize();
    sign.clear();
    
    // Run socket server
    run_socket_server(sign);
    
    return 0;
}

