#!/bin/bash

# This function will print its argument, preceded and followed by a line of '-'
# as long as the argument.
print_banner() {
    local len=${#1}
    for i in $(seq 1 $len); do echo -n "-"; done
    echo -e "\n${1}"
    for i in $(seq 1 $len); do echo -n "-"; done
    echo
}

# Store the working directory of this script.
here=$(dirname ${0})

# Define text formatting commands.
# - textbf: Use bold-face.
# - textnm: Reset to normal.
# - startul: Start underlined text.
# - endul: End underlined text.
textbf=$(tput bold)
textnm=$(tput sgr0)
startul=$(tput smul)
endul=$(tput rmul)

# Set option defaults.
silent=0
time_step=0
progdir=${here}

# This is the CLI's main help text.
show_help()
{
    cli_name=${0##*/}
    echo "
${textbf}NAME${textnm}
        $cli_name - Run streams3D.py

${textbf}SYNOPSIS${textnm}
        ${textbf}$cli_name${textnm} [${startul}OPTION${endul}] ${startul}NAME${endul}

${textbf}DESCRIPTION${textnm}

        ${textbf}-h${textnm}, ${textbf}--help${textnm}
                Display help and exit.
        ${textbf}-s${textnm}, ${textbf}--silent${textnm}
                Suppress runtime messages.
        ${textbf}-t N${textnm}, ${textbf}--timestep=N${textnm}
                The integer simulation time step to show (default: ${timestep}).
        ${textbf}-d DIR${textnm}, ${textbf}--directory=DIR${textnm}
                The directory containing the version of the Python program to 
                run (default: ${progdir}).
"
}

# This will run if the CLI gets an unrecognized option.
report_bad_arg()
{
    printf "\nUnrecognized command: ${1}\n\n"
}

# Parse command-line options. See
# `/usr/share/doc/util-linux/examples/getopt-example.bash` and the `getopt`
# manual page for more information.
TEMP=$(getopt \
    -n 'main.sh' \
    -o '-hst:d:' \
    -l 'help,silent' \
    -l 'timestep:' \
    -l 'directory:' \
    -- "$@")

if [ $? -ne 0 ]; then
    echo "Failed to parse command-line arguments. Terminating."
    exit 1
fi

eval set -- "$TEMP"
unset TEMP

while [ $# -gt 0 ]; do
    case "$1" in
        '-h'|'--help')
            show_help
            exit
        ;;
        '-s'|'--silent')
            silent=1
            shift
            continue
        ;;
        '-t'|'--timestep')
            time_step=${2}
            shift 2
            continue
        ;;
        '-d'|'--directory')
            progdir=${2}
            shift 2
            continue
        ;;
        '--')
            shift
            break
        ;;
        *)
            quantity="${1}"
            shift
            continue
        ;;
    esac
done

# Get the full path to the plotting program.
prog=$(readlink -f ${progdir}/streams3D.py)
if [ ! -f ${prog} ]; then
    echo "The file ${prog} does not exist"
    exit 1
fi

# Parse the required physical quantity from the remaining arguments.
# quantity="${1}"
if [ -z "${quantity}" ]; then
    echo "Missing name of the physical quantity to plot"
    exit 1
fi
shift

# Collect extra arguments. These may indicate that the user incorrectly entered
# an argument.
extra_args="$@"
if [ -n "${extra_args}" ]; then
    echo
    echo "Found the following unrecognized argument(s):"
    echo
    for arg in ${extra_args[@]}; do
        echo ">   $arg"
    done
    echo
    echo "Did you misspell something?"
    echo
    echo "Note that this program does not support passing arbitrary arguments"
    echo "to the visualization routine."
    echo
    exit 1
fi

pushd ${here} &> /dev/null

datadir=$(readlink -e data)
confpath=eprem.cfg
plotdir=$(readlink -f figures)

echo
print_banner " Working directories "
echo "prog=${prog}"
echo "datadir=${datadir}"
echo "plotdir=${plotdir}"
echo

source $(readlink -f config/${quantity}.cfg)

print_banner " Configured parameters for '${quantity}' "
echo "mode=${mode}"
echo "colorscale=${colorscale}"
echo "datascale=${datascale}"
echo "cmin=${cmin}"
echo "cmax=${cmax}"
echo

streams=(
    0
    1
    2
    3
    4
    5
)

active_streams=${streams[@]}

axis_lim=1
axis_units="au"

energy=10.0

camera_eye=(0.50 90.0 -15.0)
marker_size=1.0
resize=active # background | active | all | none
resize_every=1
resize_by=2
resize_power=0.0

sun_color="yellow"

if [ ${#active_streams[@]} -eq 0 ]; then
    figname="streams3D-t${time_step}.html"
else
    figname="streams3D-${mode}-t${time_step}.html"
fi
figpath=${plotdir}/${figname}

python ${prog} \
    --datadir ${datadir} \
    --confpath ${confpath} \
    --streams ${streams[@]} \
    --active_streams ${active_streams[@]} \
    --mode "${mode}" \
    --colorscale "${colorscale}" \
    --cmin ${cmin} \
    --cmax ${cmax} \
    --datascale "${datascale}" \
    --time_step ${time_step} \
    --energy ${energy} \
    --xaxis_range -${axis_lim} +${axis_lim} \
    --yaxis_range -${axis_lim} +${axis_lim} \
    --zaxis_range -${axis_lim} +${axis_lim} \
    --axis_units "${axis_units}" \
    --camera_eye ${camera_eye[@]} \
    --eye_in_rtp \
    --marker_size ${marker_size} \
    --resize ${resize} \
    --resize_every ${resize_every} \
    --resize_by ${resize_by} \
    --resize_power ${resize_power} \
    --sun_color "${sun_color}" \
    --figpath "${figpath}" \
    @"${config}" \
    -v

popd ${here} &> /dev/null
