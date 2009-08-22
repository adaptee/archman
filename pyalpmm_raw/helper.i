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
    pmdepend_t *tmp;
    tmp = (pmdepend_t*) alpm_list_getdata(item);
    printf("HASIDIHSADHIASD C++++");
    char *s;
    s = tmp->name;
    printf("%s", &s);
    return tmp;
}

//pmpkg_t *helper_list_getsyncpkg(alpm_list_t *item){
//    return alpm_sync_get_pkg((pmsyncpkg_t *) alpm_list_getdata(item));
//}

pmfileconflict_t *helper_list_getfileconflict(alpm_list_t *item){
    return (pmfileconflict_t*) alpm_list_getdata(item);
}

static alpm_list_t *list_buffer = NULL;

alpm_list_t **get_list_buffer_ptr(){
    return &list_buffer;
}

alpm_list_t *get_list_from_ptr(alpm_list_t **d){
    return *d;
}

alpm_list_t *helper_create_alpm_list(PyObject *list) {
    int i;
    alpm_list_t *out = NULL;

    for(i=0; i<PyList_Size(list); ++i)
        out = alpm_list_add(out, PyString_AsString(PyList_GetItem(list, i)));
    return out;
}

char *helper_get_char(PyObject *str){
    return PyString_AsString(str);
}

int get_errno(){
    return (int) pm_errno;
}


%}
