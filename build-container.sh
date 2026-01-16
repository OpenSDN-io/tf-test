#!/bin/bash

echo "Run build-container.sh with params $@"

REGISTRY_SERVER="opencontrail"
TAG=""

LINUX_ID=$(awk -F"=" '/^ID=/{print $2}' /etc/os-release | tr -d '"')
LINUX_VER_ID=$(awk -F"=" '/^VERSION_ID=/{print $2}' /etc/os-release | tr -d '"')

#SITE_MIRROR is an URL to the root of cache. This code will look for the files inside predefined folder
[ -z "${SITE_MIRROR}" ] || SITE_MIRROR="${SITE_MIRROR}/external-web-cache"

download_pkg () {
    local pkg=$1
    local dir=$2
    if [[ $pkg =~ ^http[s]*:// ]]; then
        wget --spider $pkg
        filename="${pkg##*/}"
        wget $pkg -O $dir/$filename
    elif [[ $pkg =~ ^ssh[s]*:// ]]; then
        server=$(echo $pkg | sed 's=scp://==;s|\/.*||')
        path=$(echo $pkg |sed -r 's#scp://[a-zA-Z0-9_\.\-]+##')
        dnf install -y sshpass
        sshpass -e scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${sshuser_sub}${server}:${path} $dir
    else
        echo "ERROR, Unknown url format, only http[s], ssh supported" >&2
        exit 1
    fi
}

docker_build_test_sku () {
    local dir=${1%/}
    local name=$2
    local tag=$3
    local build_arg_opts=$4
    local build_arg_opts+=' --network host'
    local dockerfile=${dir}'/Dockerfile'
    local docker_ver=$(sudo docker -v | awk -F' ' '{print $3}' | sed 's/,//g')
    build_arg_opts+=" --build-arg REGISTRY_SERVER=${REGISTRY_SERVER}"
    build_arg_opts+=" --build-arg PIP_REPOSITORY=${PIP_REPOSITORY}"
    build_arg_opts+=" --build-arg DOCKERFILE_DIR=${dir}"
    [ -z "$SITE_MIRROR" ] || build_arg_opts+=" --build-arg SITE_MIRROR=${SITE_MIRROR}"
    echo "Building test container ${name}:${tag} (sudo docker build ${build_arg_opts} -t ${name}:${tag} -f $dockerfile .)"
    sudo docker build ${build_arg_opts} -t ${name}:${tag} -f $dockerfile . || exit 1
    echo "Built test container ${name}:${tag}"
}

docker_build_test () {
    REGISTRY_SERVER=""
    usage () {
    cat <<EOF
Build test container

Usage: $0 test [OPTIONS]

  -h|--help                     Print help message
  --tag           TAG           Docker container tag
  --registry-server REGISTRY_SERVER Docker registry hosting the base test container, Defaults to docker.io/opencontrail
  --post          POST          Upload the test container to the registy-server, if specified
EOF
    }
    if ! options=$(getopt -o h -l help,tag:,registry-server:,post -- "$@"); then
        usage
        exit 1
    fi
    eval set -- "$options"

    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help) usage; exit;;
            --tag) TAG=$2; shift;;
            --registry-server) REGISTRY_SERVER=$2; shift;;
            --post) POST=1; shift;;
        esac
        shift
    done

    if [[ -z $REGISTRY_SERVER ]]; then
        echo "--registry-server is unspecified, using docker.io/opencontrail"; echo
    fi
    if [[ -z $TAG ]]; then
        echo "TAG(--tag) is unspecified. using 'ocata'"; echo
        TAG=ocata
    fi

    local dockerfile='docker/Dockerfile'
    local build_arg_opts="--network host"
    if [[ -n "$LINUX_DISTR" && -n "$LINUX_DISTR_VER" ]] ; then
        if [[ "$LINUX_DISTR" =~ 'ubi8' ]] ; then
            local docker_ver=$(sudo docker -v | awk -F' ' '{print $3}' | sed 's/,//g')
            if [[ "$docker_ver" < '17.06' ]] ; then
                cat $dockerfile | sed \
                    -e "s|^FROM \$LINUX_DISTR:\$LINUX_DISTR_VER|FROM $LINUX_DISTR:$LINUX_DISTR_VER|" \
                    > ${dockerfile}.nofromargs
                dockerfile="${dockerfile}.nofromargs"
            else
                build_arg_opts+=" --build-arg LINUX_DISTR=${LINUX_DISTR}"
                build_arg_opts+=" --build-arg LINUX_DISTR_VER=${LINUX_DISTR_VER}"
            fi
        fi
    fi
    if [[ -n "$CONTRAIL_REGISTRY" && -n "$CONTRAIL_CONTAINER_TAG" ]] ; then
        build_arg_opts+=" --build-arg CONTRAIL_REGISTRY=${CONTRAIL_REGISTRY}"
        build_arg_opts+=" --build-arg CONTRAIL_CONTAINER_TAG=${CONTRAIL_CONTAINER_TAG}"
    fi
    if [[ -n "$SITE_MIRROR" ]] ; then
        build_arg_opts+=" --build-arg SITE_MIRROR=${SITE_MIRROR}"
    fi
    if [[ "$LINUX_ID" == 'rhel' && "${LINUX_VER_ID//.[0-9]*/}" == '8' ]] ; then
        # podman case
        build_arg_opts+=' --format docker'
        build_arg_opts+=' --cap-add=all --security-opt label=disable  --security-opt seccomp=unconfined'
        build_arg_opts+=' -v /etc/resolv.conf:/etc/resolv.conf:ro'
        # to make posible use subscription inside container run from container in podman
        if [ -e /run/secrets/etc-pki-entitlement ] ; then
            build_arg_opts+=' -v /run/secrets/etc-pki-entitlement:/run/secrets/etc-pki-entitlement:ro'
        fi
    fi
    echo "Waiting for base container"
    # don't use 'pull' - it may download old version from internet. just wait for local build
    while ! sudo docker inspect ${CONTRAIL_REGISTRY}/opensdn-base:${CONTRAIL_CONTAINER_TAG} 2>/dev/null ; do
        printf "."
        i=$((i + 1))
        if (( i > 30 )) ; then
            echo ""
            echo "ERROR: ${CONTRAIL_REGISTRY}/opensdn-base:${CONTRAIL_CONTAINER_TAG} not found"
            return 1
        fi
        sleep 30
    done

    docker_build_test_sku "docker" "opensdn-test-test" "$TAG" "$build_arg_opts"
    sudo docker tag opensdn-test-test:$TAG $REGISTRY_SERVER/opensdn-test-test:$TAG
    if [[ -n $POST ]]; then
        sudo docker push $REGISTRY_SERVER/opensdn-test-test:$TAG
    fi
}

usage () {
    cat <<EOF
Build of contrail test container

Usage: $0 test [OPTIONS]

Subcommands:

test   Build contrail test container openstack/contrail version specific

Run $0 <Subcommand> -h|--help to get subcommand specific help

EOF
}

if [[ -n $SSHUSER ]]; then
   sshuser_sub="${SSHUSER}@"
fi
subcommand=$1; shift;
if [[ $subcommand == '-h' || $subcommand == '' || $subcommand == '--help' ]]; then
    usage
    exit
elif [[ $subcommand == 'test' ]]; then
    docker_build_test $@
elif [[ $subcommand == 'base' ]]; then
    echo "Error: '$subcommand' is not supported anymore. Build test." >&2
else
    echo "Error: '$subcommand' is not a known subcommand." >&2
    echo "       Run '$0 --help' for a list of known subcommands." >&2
    exit 1
fi
