%inline %{



pmpkg_t *helper_list_getpkg(alpm_list_t *item){
    return (pmpkg_t*) alpm_list_getdata(item);
}

char *helper_list_getstr(alpm_list_t *item){
    return (char*) alpm_list_getdata(item);
}

pmgrp_t *helper_list_getgrp(alpm_list_t *item){
    return (pmgrp_t*) alpm_list_getdata(item);
}

pmdepmissing_t *helper_list_getmiss(alpm_list_t *item){
    return (pmdepmissing_t*) alpm_list_getdata(item);
}

pmdepend_t *helper_list_getdep(alpm_list_t *item){
    return (pmdepend_t*) alpm_list_getdata(item);
}

pmpkg_t *helper_list_getsyncpkg(alpm_list_t *item){
    return alpm_sync_get_pkg((pmsyncpkg_t *) alpm_list_getdata(item));
}

alpm_list_t *list_buffer = NULL;
alpm_list_t **get_list_buffer_ptr(){
    return &list_buffer;
}

alpm_list_t *get_list_from_ptr(alpm_list_t **d){
    return *d;
}


int get_errno(){
    return (int) pm_errno;
}


%}
